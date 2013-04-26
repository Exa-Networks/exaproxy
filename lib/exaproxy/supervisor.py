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


from .util.pid import PID
from .util.daemon import Daemon

from .reactor.redirector.manager import RedirectorManager
from .reactor.content.manager import ContentManager
from .reactor.client.manager import ClientManager
from .reactor.resolver.manager import ResolverManager
from .network.async import Poller
from .network.server import Server
from .html.page import Page
from .monitor import Monitor

from .reactor import Reactor

from .configuration import load
from exaproxy.util.log.logger import Logger
from exaproxy.util.log.writer import SysLogWriter
from exaproxy.util.log.writer import UsageWriter

from exaproxy.util.interfaces import getifaddrs,AF_INET,AF_INET6

class Supervisor(object):
	alarm_time = 0.1                           # regular backend work
	history_frequency = int(1/alarm_time)      # when we record history
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

		self.poller.setupRead('read_proxy')           # Listening proxy sockets
		self.poller.setupRead('read_web')             # Listening webserver sockets
		self.poller.setupRead('read_workers')         # Pipes carrying responses from the child processes
		self.poller.setupRead('read_resolver')        # Sockets currently listening for DNS responses

		self.poller.setupRead('read_client')          # Active clients
		self.poller.setupRead('opening_client')       # Clients we have not yet read a request from
		self.poller.setupWrite('write_client')        # Active clients with buffered data to send
		self.poller.setupWrite('write_resolver')      # Active DNS requests with buffered data to send

		self.poller.setupRead('read_download')        # Established connections
		self.poller.setupWrite('write_download')      # Established connections we have buffered data to send to
		self.poller.setupWrite('opening_download')    # Opening connections

		self.monitor = Monitor(self)
		self.page = Page(self)
		self.manager = RedirectorManager(
			self.configuration,
			self.poller,
		)
		self.content = ContentManager(self,configuration)
		self.client = ClientManager(self.poller, configuration)
		self.resolver = ResolverManager(self.poller, self.configuration, configuration.dns.retries*10)
		self.proxy = Server('http proxy',self.poller,'read_proxy', configuration.http.connections)
		self.web = Server('web server',self.poller,'read_web', configuration.web.connections)

		self.reactor = Reactor(self.configuration, self.web, self.proxy, self.manager, self.content, self.client, self.resolver, self.log_writer, self.usage_writer, self.poller)

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

		signal.signal(signal.SIGALRM, self.sigalrm)

		# make sure we always have data in history, here as record() requires self to be partially initialised to run
		self.monitor.record()

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


	def sigalrm (self,signum, frame):
		self.signal_log.debug('SIG ALRM received, timed actions')
		self.reactor.running = False
		signal.setitimer(signal.ITIMER_REAL,self.alarm_time,self.alarm_time)


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
		if self.daemon.drop_privileges():
			self.log.stdout('Could not drop privileges to \'%s\'. Refusing to run as root' % self.daemon.user)
			self.log.stdout('Set the environment value USER to change the unprivileged user')
			return

		if not self.initialise():
			self._shutdown = True

		signal.setitimer(signal.ITIMER_REAL,self.alarm_time,self.alarm_time)

		count_history = 0
		count_increase = 0
		count_decrease = 0
		count_saturation = 0
		count_interface = 0

		while True:
			count_history = (count_history + 1) % self.history_frequency
			count_increase = (count_increase + 1) % self.increase_frequency
			count_decrease = (count_decrease + 1) % self.decrease_frequency
			count_saturation = (count_saturation + 1) % self.saturation_frequency
			count_interface = (count_interface + 1) % self.interface_frequency

			try:
				if self._pdb:
					self._pdb = False
					import pdb
					pdb.set_trace()


				# check for IO change with select
				self.reactor.run()


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


				if self._increase_spawn_limit:
					number = self._increase_spawn_limit
					self._increase_spawn_limit = 0
					self.manager.low += number
					self.manager.high = max(self.manager.low,self.manager.high)
					for _ in range(number):
						self.manager.increase()

				if self._decrease_spawn_limit:
					number = self._decrease_spawn_limit
					self._decrease_spawn_limit = 0
					self.manager.high = max(1,self.manager.high-number)
					self.manager.low = min(self.manager.high,self.manager.low)
					for _ in range(number):
						self.manager.decrease()


				# save our monitoring stats
				if count_history == 0:
					self.monitor.record()

				# make sure we have enough workers
				if count_increase == 0:
					self.manager.provision()
				# and every so often remove useless workers
				if count_decrease == 0:
					self.manager.deprovision()

				# report if we saw too many connections
				if count_saturation == 0:
					self.proxy.saturation()
					self.web.saturation()

				if count_interface == 0:
					self.interfaces()

			except KeyboardInterrupt:
				self.log.info('^C received')
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
		# start our threads
		self.manager.start()


		# only start listening once we know we were able to fork our worker processes
		tcp4 = self.configuration.tcp4
		tcp6 = self.configuration.tcp6

		ok = bool(tcp4.listen or tcp6.listen)
		if not ok:
			self.log.error('Not listening on IPv4 or IPv6.')

		if ok and tcp4.listen:
			s = self.proxy.listen(tcp4.host,tcp4.port, tcp4.timeout, tcp4.backlog)
			ok = bool(s)
			if not s:
				print >> sys.stderr, 'IPv4 proxy, unable to listen on %s:%s' % (tcp4.host,tcp4.port)
				self.log.error('IPv4 proxy, unable to listen on %s:%s' % (tcp4.host,tcp4.port))

		if ok and tcp6.listen:
			s = self.proxy.listen(tcp6.host,tcp6.port, tcp6.timeout, tcp6.backlog)
			ok = bool(s)
			if not s:
				print >> sys.stderr, 'IPv6 proxy, unable to listen on %s:%s' % (tcp6.host,tcp6.port)
				self.log.error('IPv6 proxy, unable to listen on %s:%s' % (tcp6.host,tcp6.port))


		if ok and self.configuration.web.enable:
			s = self.web.listen(self.configuration.web.host,self.configuration.web.port, 10, 10)
			if not s:
				print >> sys.stderr, 'internal web server, unable to listen on %s:%s' % (self.configuration.web.host, self.configuration.web.port)
				self.log.error('internal web server, unable to listen on %s:%s' % (self.configuration.web.host, self.configuration.web.port))
				ok = False

		return ok

	def shutdown (self):
		"""terminate all the current BGP connections"""
		self.log.info('Performing shutdown')
		try:
			self.web.stop()  # accept no new web connection
			self.proxy.stop()  # accept no new proxy connections
			self.manager.stop()  # shut down redirector children
			os.kill(os.getpid(),signal.SIGALRM)
			self.content.stop()  # stop downloading data
			self.client.stop()  # close client connections
			self.pid.remove()
		except KeyboardInterrupt:
			self.log.info('^C received while shutting down. Exiting immediately because you insisted.')
			sys.exit()

	def reload (self):
		self.log.info('Performing reload of exaproxy %s' % self.configuration.proxy.version ,'supervisor')
		self.manager.respawn()
