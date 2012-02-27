#!/usr/bin/env python
# encoding: utf-8
"""
supervisor.py

Created by Thomas Mangin on 2011-11-29.
Copyright (c) 2011 Exa Networks. All rights reserved.
"""

import os
import sys
import signal

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

from .util.logger import logger

from .configuration import load

class Supervisor(object):
	alarm_time = 1
	# import os
	# clear = [hex(ord(c)) for c in os.popen('clear').read()]
	# clear = ''.join([chr(int(c,16)) for c in ['0x1b', '0x5b', '0x48', '0x1b', '0x5b', '0x32', '0x4a']])

	def __init__ (self):
		logger.info('supervisor','starting %s' % sys.argv[0])
		logger.info('supervisor','python version %s' % sys.version.replace(os.linesep,' '))

		self.configuration = load()

		self.pid = PID(self.configuration.daemon.pidfile)

		self.daemon = Daemon(self.configuration.daemon)
		self.poller = Poller(self.configuration.daemon)

		self.poller.setupRead('read_proxy')           # Listening proxy sockets
		self.poller.setupRead('read_web')             # Listening webserver sockets
		self.poller.setupRead('read_workers')         # Pipes carrying responses from the child processes
		self.poller.setupRead('read_resolver')       # Sockets currently listening for DNS responses

		self.poller.setupRead('read_client')          # Active clients
		self.poller.setupRead('opening_client')       # Clients we have not yet read a request from
		self.poller.setupWrite('write_client')        # Active clients with buffered data to send
		self.poller.setupWrite('write_resolver')      # Active DNS requests with buffered data to send

		self.poller.setupRead('read_download')        # Established connections
		self.poller.setupWrite('write_download')      # Established connections we have buffered data to send to
		self.poller.setupWrite('opening_download')    # Opening connections

		self.monitor = Monitor(self)
		self.page = Page(self.monitor)
		self.manager = RedirectorManager(
			self.configuration,
			self.poller,
		)
		self.content = ContentManager(self.poller, self.configuration.web.html, self.page)
		self.client = ClientManager(self.poller)
		self.resolver = ResolverManager(self.poller, self.configuration)
		self.proxy = Server(self.poller,'read_proxy')
		self.web = Server(self.poller,'read_web')

		self.reactor = Reactor(self.web, self.proxy, self.manager, self.content, self.client, self.resolver, self.poller)

		# Only here so the introspection code can find them
		self.logger = logger

		self._shutdown = False
		self._reload = False
		self._toggle_debug = False
		self._decrease_spawn_limit = False
		self._increase_spawn_limit = False
		self._refork = True
		self._timer = False

		signal.signal(signal.SIGTERM, self.sigterm)
		signal.signal(signal.SIGHUP, self.sighup)
		signal.signal(signal.SIGALRM, self.sigalrm)
		signal.signal(signal.SIGUSR1, self.sigusr1)
		signal.signal(signal.SIGUSR2, self.sigusr2)
		signal.signal(signal.SIGTRAP, self.sigtrap)
		signal.signal(signal.SIGABRT, self.sigabrt)


	def sigterm (self,signum, frame):
		logger.info('signal','SIG TERM received, shutdown request')
		self._shutdown = True

	def sighup (self,signum, frame):
		logger.info('signal','SIG HUP received, reload request')
		self._reload = True

	def sigtrap (self,signum, frame):
		logger.info('signal','SIG TRAP received, toggle logger')
		self._toggle_debug = True

	def sigusr1 (self,signum, frame):
		logger.info('signal','SIG USR1 received, decrease worker number')
		self._decrease_spawn_limit = True

	def sigusr2 (self,signum, frame):
		logger.info('signal','SIG USR2 received, increase worker number')
		self._increase_spawn_limit = True

	def sigabrt (self,signum, frame):
		logger.info('signal','SIG INFO received, refork request')
		self._refork = True

	def sigalrm (self,signum, frame):
		logger.debug('signal','SIG ALRM received, timed actions')
		self._timer = True
		self.reactor.running = False
		signal.alarm(self.alarm_time)

	def run (self):
		if self.daemon.drop_privileges():
			logger.warning('supervisor','Could not drop privileges to \'%s\' refusing to run as root' % self.daemon.user)
			logger.warning('supervisor','Set the environmemnt value USER to change the unprivileged user')
			return

		ok = self.initialise()
		if not ok:
			self._shutdown = True

		signal.alarm(self.alarm_time)

		while True:
			try:
				if self._toggle_debug:
					self._toggle_debug = False
					logger.toggle()

				if self._shutdown:
					self._shutdown = False
					self.shutdown()
					break
				elif self._reload:
					self._reload = False
					self.reload()
				elif self._refork:
					self._refork = False
					logger.warning('signal','refork not implemented')
					# stop listening to new connections
					# refork the program (as we have been updated)
					# just handle current open connection

				if self._increase_spawn_limit:
					self._increase_spawn_limit = False
					if self.manager.low == self.manager.high: self.manager.high += 1
					self.manager.low = min(self.manager.high,self.manager.low+1)

				if self._decrease_spawn_limit:
					self._decrease_spawn_limit = False
					if self.manager.high >1: self.manager.high -= 1
					self.manager.low = min(self.manager.high,self.manager.low)

				# check for IO change with select
				self.reactor.running = True
				self.reactor.run()

				# Quit on problems which can not be fixed (like running out of file descriptor)
				#self._shutdown = not self.reactor.running

				if self._timer:
					self._timer = False
					# save our monitoring stats
					self.monitor.record()
					# make sure we have enough workers
					self.manager.provision()

			except KeyboardInterrupt:
				logger.info('supervisor','^C received')
				self._shutdown = True
			except OSError,e:
				# XXX: we need to stop listening and re-fork ourselves
				if e.errno == 24: #Too many open files
					logger.critical('supervisor','Too many opened files, shutting down')
					self._shutfown = True
				else:
					# Not sure we can get here but if so, let the user know
					raise

#			finally:
#				from leak import objgraph
#				print objgraph.show_most_common_types(limit=20)
#				import random
#				obj = objgraph.by_type('ReceivedRoute')[random.randint(0,2000)]
#				objgraph.show_backrefs([obj], max_depth=10)

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
			logger.error('supervisor', 'Not listening on IPv4 or IPv6.')

		if tcp4.listen:
			s = self.proxy.listen(tcp4.host,tcp4.port, tcp4.timeout, tcp4.backlog)
			ok = bool(s)
			if not s:
				logger.error('supervisor', 'Unable to listen on %s:%s' % (tcp4.host,tcp4.port))

		if tcp6.listen:
			s = self.proxy.listen(tcp6.host,tcp6.port, tcp6.timeout, tcp6.backlog)
			ok = bool(s)
			if not s:
				logger.error('supervisor', 'Unable to listen on %s:%s' % (tcp6.host,tcp6.port))


		if self.configuration.web.enable:
			s = self.web.listen(self.configuration.web.host,self.configuration.web.port, 10, 10)
			if not s:
				logger.error('supervisor', 'Unable to listen on %s:%s' % ('127.0.0.1', self.configuration.web.port))
				ok = False

		return ok

	def shutdown (self):
		"""terminate all the current BGP connections"""
		logger.info('supervisor','Performing shutdown')
		try:
			self.web.stop()  # accept no new web connection
			self.proxy.stop()  # accept no new proxy connections
			self.manager.stop()  # shut down redirector children
			os.kill(os.getpid(),signal.SIGALRM)
			self.content.stop() # stop downloading data
			self.client.stop() # close client connections
			self.pid.remove()
		except KeyboardInterrupt:
			logger.info('supervisor','^C received while shutting down. Exiting immediately because you insisted.')
			sys.exit()

	def reload (self):
		logger.info('supervisor','Performing reload of exaproxy %s' % self.configuration.proxy.version ,'supervisor')
		self.manager.respawn()
