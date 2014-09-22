# encoding: utf-8
"""
supervisor.py

Created by Thomas Mangin on 2011-11-29.
Copyright (c) 2011-2013  Exa Networks. All rights reserved.
"""

import os
import sys
import signal
import traceback
from socket import has_ipv6

from .util.pid import PID
from .util.daemon import Daemon
from .util.alarm import alarm_thread

from .reactor.content.manager import ContentManager
from .reactor.client.manager import ClientManager
from .reactor.resolver.manager import ResolverManager
from .network.async import Poller
from .network.server import Server
from .html.page import Page
from .monitor import Monitor

from .reactor import Reactor
from .reactor.redirector import fork_redirector
from .reactor.redirector import redirector_message_thread

from .configuration import load
from exaproxy.util.log.logger import Logger
from exaproxy.util.log.writer import SysLogWriter
from exaproxy.util.log.writer import UsageWriter

from exaproxy.util.interfaces import getifaddrs,AF_INET,AF_INET6

class Supervisor (object):
	alarm_time = 0.1                           # regular backend work
	second_frequency = int(1/alarm_time)       # when we record history
	minute_frequency = int(60/alarm_time)      # when we want to average history
	increase_frequency = int(5/alarm_time)     # when we add workers
	decrease_frequency = int(60/alarm_time)    # when we remove workers
	saturation_frequency = int(20/alarm_time)  # when we report connection saturation
	interface_frequency = int(300/alarm_time)  # when we check for new interfaces

	# import os
	# clear = [hex(ord(c)) for c in os.popen('clear').read()]
	# clear = ''.join([chr(int(c,16)) for c in ['0x1b', '0x5b', '0x48', '0x1b', '0x5b', '0x32', '0x4a']])

	def __init__ (self,configuration):
		configuration = load()
		self.configuration = configuration

		# Only here so the introspection code can find them
		self.log = Logger('supervisor', configuration.log.supervisor)
		self.log.error('Starting exaproxy version %s' % configuration.proxy.version)

		self.signal_log = Logger('signal', configuration.log.signal)
		self.log_writer = SysLogWriter('log', configuration.log.destination, configuration.log.enable, level=configuration.log.level)
		self.usage_writer = UsageWriter('usage', configuration.usage.destination, configuration.usage.enable)

		sys.exitfunc = self.log_writer.writeMessages

		self.log_writer.setIdentifier(configuration.daemon.identifier)
		#self.usage_writer.setIdentifier(configuration.daemon.identifier)

		if configuration.debug.log:
			self.log_writer.toggleDebug()
			self.usage_writer.toggleDebug()

		self.log.error('python version %s' % sys.version.replace(os.linesep,' '))
		self.log.debug('starting %s' % sys.argv[0])

		self.pid = PID(self.configuration)

		self.daemon = Daemon(self.configuration)
		self.poller = Poller(self.configuration.daemon)

		self.poller.setupRead('read_proxy')       # Listening proxy sockets
		self.poller.setupRead('read_web')         # Listening webserver sockets
		self.poller.setupRead('read_icap')        # Listening icap sockets
		self.poller.setupRead('read_redirector')  # Pipes carrying responses from the redirector process
		self.poller.setupRead('read_resolver')    # Sockets currently listening for DNS responses

		self.poller.setupRead('read_client')      # Active clients
		self.poller.setupRead('opening_client')   # Clients we have not yet read a request from
		self.poller.setupWrite('write_client')    # Active clients with buffered data to send
		self.poller.setupWrite('write_resolver')  # Active DNS requests with buffered data to send

		self.poller.setupRead('read_download')      # Established connections
		self.poller.setupWrite('write_download')    # Established connections we have buffered data to send to
		self.poller.setupWrite('opening_download')  # Opening connections

		self.poller.setupRead('read_interrupt')		# Scheduled events
		self.poller.setupRead('read_control')		# Responses from commands sent to the redirector process

		self.monitor = Monitor(self)
		self.page = Page(self)
		self.content = ContentManager(self,configuration)
		self.client = ClientManager(self.poller, configuration)
		self.resolver = ResolverManager(self.poller, self.configuration, configuration.dns.retries*10)
		self.proxy = Server('http proxy',self.poller,'read_proxy', configuration.http.connections)
		self.web = Server('web server',self.poller,'read_web', configuration.web.connections)
		self.icap = Server('icap server',self.poller,'read_icap', configuration.icap.connections)

		self._shutdown = True if self.daemon.filemax == 0 else False  # stop the program
		self._softstop = False  # stop once all current connection have been dealt with
		self._reload = False  # unimplemented
		self._toggle_debug = False  # start logging a lot
		self._decrease_spawn_limit = 0
		self._increase_spawn_limit = 0
		self._refork = False  # unimplemented
		self._pdb = False  # turn on pdb debugging
		self._listen = None  # listening change ? None: no, True: listen, False: stop listeing
		self.wait_time = 5.0  # how long do we wait at maximum once we have been soft-killed
		self.local = set()  # what addresses are on our local interfaces

		if not self.initialise():
			self._shutdown = True

		elif self.daemon.drop_privileges():
			self.log.critical('Could not drop privileges to \'%s\'. Refusing to run as root' % self.daemon.user)
			self.log.critical('Set the environment value USER to change the unprivileged user')
			self._shutdown = True

		# fork the redirector process before performing any further setup
		redirector = fork_redirector(self.poller, self.configuration)

		# NOTE: create threads _after_ all forking is done

		# regularly interrupt the reactor for maintenance
		self.interrupt_scheduler = alarm_thread(self.poller, self.alarm_time)

		# use simple blocking IO for communication with the redirector process
		self.redirector = redirector_message_thread(redirector)

		self.reactor = Reactor(self.configuration, self.web, self.proxy, self.icap, self.redirector, self.content, self.client, self.resolver, self.log_writer, self.usage_writer, self.poller)

		self.interfaces()

		signal.signal(signal.SIGQUIT, self.sigquit)
		signal.signal(signal.SIGINT, self.sigterm)
		signal.signal(signal.SIGTERM, self.sigterm)
		# signal.signal(signal.SIGABRT, self.sigabrt)
		# signal.signal(signal.SIGHUP, self.sighup)

		signal.signal(signal.SIGTRAP, self.sigtrap)

		signal.signal(signal.SIGUSR1, self.sigusr1)
		signal.signal(signal.SIGUSR2, self.sigusr2)
		signal.signal(signal.SIGTTOU, self.sigttou)
		signal.signal(signal.SIGTTIN, self.sigttin)

		# make sure we always have data in history
		# (done in zero for dependencies reasons)

		self.redirector.requestStats()
		command, control_data = self.redirector.readResponse()
		stats_data = control_data if command == 'STATS' else None

		stats = self.monitor.statistics(stats_data)
		ok = self.monitor.zero(stats)

		if ok:
			self.redirector.requestStats()

		else:
			self._shutdown = True

	def exit (self):
		sys.exit()

	def sigquit (self,signum, frame):
		if self._softstop:
			self.signal_log.critical('multiple SIG INT received, shutdown')
			self._shutdown = True
		else:
			self.signal_log.critical('SIG INT received, soft-stop')
			self._softstop = True
			self._listen = False

	def sigterm (self,signum, frame):
		self.signal_log.critical('SIG TERM received, shutdown request')
		if os.environ.get('PDB',False):
			self._pdb = True
		else:
			self._shutdown = True

	# def sigabrt (self,signum, frame):
	# 	self.signal_log.info('SIG INFO received, refork request')
	# 	self._refork = True

	# def sighup (self,signum, frame):
	# 	self.signal_log.info('SIG HUP received, reload request')
	# 	self._reload = True

	def sigtrap (self,signum, frame):
		self.signal_log.critical('SIG TRAP received, toggle debug')
		self._toggle_debug = True


	def sigusr1 (self,signum, frame):
		self.signal_log.critical('SIG USR1 received, decrease worker number')
		self._decrease_spawn_limit += 1

	def sigusr2 (self,signum, frame):
		self.signal_log.critical('SIG USR2 received, increase worker number')
		self._increase_spawn_limit += 1


	def sigttou (self,signum, frame):
		self.signal_log.critical('SIG TTOU received, stop listening')
		self._listen = False

	def sigttin (self,signum, frame):
		self.signal_log.critical('SIG IN received, star listening')
		self._listen = True


	def interfaces (self):
		local = set(['127.0.0.1','::1'])
		for interface in getifaddrs():
			if interface.family not in (AF_INET,AF_INET6):
				continue
			if interface.address not in self.local:
				self.log.info('found new local ip %s (%s)' % (interface.address,interface.name))
			local.add(interface.address)
		for ip in self.local:
			if ip not in local:
				self.log.info('removed local ip %s' % ip)
		if local == self.local:
			self.log.info('no ip change')
		else:
			self.local = local

	def run (self):
		count_second = 0
		count_minute = 0
		count_saturation = 0
		count_interface = 0

		while True:
			count_second = (count_second + 1) % self.second_frequency
			count_minute = (count_minute + 1) % self.minute_frequency

			count_saturation = (count_saturation + 1) % self.saturation_frequency
			count_interface = (count_interface + 1) % self.interface_frequency

			try:
				if self._pdb:
					self._pdb = False
					import pdb
					pdb.set_trace()

				# prime the alarm
				self.interrupt_scheduler.setAlarm()

				# check for IO change with select
				status, events = self.reactor.run()

				# shut down the server if a child process disappears
				if status is False:
					self._shutdown = True

				# clear the alarm condition
				self.interrupt_scheduler.acknowledgeAlarm()

				# must follow the reactor so we are sure to go through the reactor at least once
				# and flush any logs
				if self._shutdown:
					self._shutdown = False
					self.shutdown()
					break
				elif self._reload:
					self._reload = False
					self.reload()
				elif self._refork:
					self._refork = False
					self.signal_log.warning('refork not implemented')
					# stop listening to new connections
					# refork the program (as we have been updated)
					# just handle current open connection


				if self._softstop:
					if self._listen == False:
						self.proxy.rejecting()
						self._listen = None
					if self.client.softstop():
						self._shutdown = True
				# only change listening if we are not shutting down
				elif self._listen is not None:
					if self._listen:
						self._shutdown = not self.proxy.accepting()
						self._listen = None
					else:
						self.proxy.rejecting()
						self._listen = None


				if self._toggle_debug:
					self._toggle_debug = False
					self.log_writer.toggleDebug()


				if self._decrease_spawn_limit:
					count = self._decrease_spawn_limit
					self.redirector.decreaseSpawnLimit(count)
					self._decrease_spawn_limit = 0

				if self._increase_spawn_limit:
					count = self._increase_spawn_limit
					self.redirector.increaseSpawnLimit(count)
					self._increase_spawn_limit = 0


				if 'read_control' in events:
					command, control_data = self.redirector.readResponse()
					stats_data = control_data if command == 'STATS' else None

				else:
					stats_data = None

				if stats_data is not None:
					# parse the data we were sent
					stats = self.monitor.statistics(stats_data)

					# and request more for the next maintenance window
					self.redirector.requestStats()

					# save our monitoring stats
					if count_second == 0:
						ok = self.monitor.second(stats)
					else:
						ok = True
						expired = 0

					if ok is True and count_minute == 0:
						ok = self.monitor.minute(stats)

					if ok is not True:
						self._shutdown = True

				# cleanup idle connections
				# TODO: track all idle connections, not just the ones that have never sent data
				expired = self.reactor.client.expire()

				if expired:
					self.proxy.notifyClose(None, count=expired)

				# report if we saw too many connections
				if count_saturation == 0:
					self.proxy.saturation()
					self.web.saturation()

				if self.configuration.daemon.poll_interfaces and count_interface == 0:
					self.interfaces()

			except KeyboardInterrupt:
				self.log.critical('^C received')
				self._shutdown = True

			except OSError,e:
				# This shoould never happen as we are limiting how many connections we accept
				if e.errno == 24:  # Too many open files
					self.log.critical('Too many opened files, shutting down')
					for line in traceback.format_exc().split('\n'):
						self.log.critical(line)
					self._shutdown = True
				else:
					self.log.critical('unrecoverable io error')
					for line in traceback.format_exc().split('\n'):
						self.log.critical(line)
					self._shutdown = True

			finally:
				pass
#				try:
#					from exaproxy.leak import objgraph
#					if objgraph:
#						count += 1
#						if count >= 30:
#							print "*"*10, time.strftime('%d-%m-%Y %H:%M:%S')
#							print objgraph.show_most_common_types(limit=20)
#							print "*"*10
#							print
#				except KeyboardInterrupt:
#					self.log.info('^C received')
#					self._shutdown = True


	def initialise (self):
		self.daemon.daemonise()
		self.pid.save()

		# only start listening once we know we were able to fork our worker processes
		tcp4 = self.configuration.tcp4
		tcp6 = self.configuration.tcp6
		icap = self.configuration.icap

		if not has_ipv6 and (tcp6.listen or tcp6.out or icap.ipv6):
			tcp6.listen = False
			tcp6.out = False
			self.log.critical('your python interpreter does not have ipv6 support !')

		out = bool(tcp4.out or tcp6.out)
		if not out:
			self.log.critical('we need to use IPv4 or IPv6 for outgoing connection - both can not be disabled !')

		listen = bool(tcp4.listen or tcp6.listen) or bool(icap.host or icap.ipv6)
		if not listen:
			self.log.critical('Not listening on either IPv4 or IPv6.')

		ok = out and listen

		if ok and tcp4.listen:
			s = self.proxy.listen(tcp4.host,tcp4.port, tcp4.timeout, tcp4.backlog)
			ok = bool(s)
			if not ok:
				self.log.critical('IPv4 proxy, unable to listen on %s:%s' % (tcp4.host,tcp4.port))

		if ok and tcp6.listen:
			s = self.proxy.listen(tcp6.host,tcp6.port, tcp6.timeout, tcp6.backlog)
			ok = bool(s)
			if not ok:
				self.log.critical('IPv6 proxy, unable to listen on %s:%s' % (tcp6.host,tcp6.port))

		if ok and icap.enable:
			s = self.icap.listen(icap.host, icap.port, tcp4.timeout, tcp4.backlog)
			ok = bool(s)
			if not ok:
				self.log.critical('ICAP server, unable to listen on %s:%s' % (icap.host, icap.port))

		if ok and icap.enable and tcp6.listen:
			s = self.icap.listen(icap.ipv6, icap.port, tcp4.timeout, tcp4.backlog)
			ok = bool(s)
			if not ok:
				self.log.critical('ICAP server, unable to listen on %s:%s' % (icap.host, icap.port))

		if ok and self.configuration.web.enable:
			s = self.web.listen(self.configuration.web.host,self.configuration.web.port, 10, 10)
			ok = bool(s)
			if not ok:
				self.log.critical('internal web server, unable to listen on %s:%s' % (self.configuration.web.host, self.configuration.web.port))

		return ok

	def shutdown (self):
		"""terminate all the current BGP connections"""
		self.log.info('Performing shutdown')
		try:
			self.web.stop()  # accept no new web connection
			self.proxy.stop()  # accept no new proxy connections
			self.redirector.stop()  # shut down redirector children
			self.content.stop()  # stop downloading data
			self.client.stop()  # close client connections
			self.pid.remove()
			self.interrupt_scheduler.stop()
		except KeyboardInterrupt:
			self.log.info('^C received while shutting down. Exiting immediately because you insisted.')
			sys.exit()

	def reload (self):
		self.log.info('Performing reload of exaproxy %s' % self.configuration.proxy.version ,'supervisor')
		self.redirector.respawn()
