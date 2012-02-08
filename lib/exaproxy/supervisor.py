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
from Queue import Queue

from .util.pid import PID
from .util.daemon import Daemon

from .classify.manager import WorkerManager
from .content.manager import ContentManager
from .client.manager import ClientManager
from .network.server import Server
from .http.page import Page

from poll import Poller
from .reactor import Reactor

from .util.logger import logger

from .configuration import configuration

class Supervisor(object):
	# import os
	# clear = [hex(ord(c)) for c in os.popen('clear').read()]
	# clear = ''.join([chr(int(c,16)) for c in ['0x1b', '0x5b', '0x48', '0x1b', '0x5b', '0x32', '0x4a']])

	def __init__ (self):
		self.pid = PID(configuration.PID)
		self.daemon = Daemon(configuration.DAEMONIZE,configuration.USER)

		self.poller = Poller(2)

		self.poller.setupRead('read_proxy')           # Listening proxy sockets
		self.poller.setupRead('read_web')             # Listening webserver sockets
		self.poller.setupRead('read_workers')         # Pipes carrying responses from the child processes

		self.poller.setupRead('read_client')          # Active clients
		self.poller.setupRead('opening_client')       # Clients we have not yet read a request from
		self.poller.setupWrite('write_client')        # Active clients with buffered data to send

		self.poller.setupRead('read_download')        # Established connections
		self.poller.setupWrite('write_download')      # Established connections we have buffered data to send to
		self.poller.setupWrite('opening_download')    # Opening connections

		self.page = Page(self)
		self.manager = WorkerManager(self.poller, configuration.PROGRAM, low=configuration.MIN_WORK, high=configuration.MAX_WORK)
		self.content = ContentManager(self.poller, configuration.HTML, self.page)
		self.client = ClientManager(self.poller)
		self.proxy = Server(self.poller,'read_proxy')
		self.web = Server(self.poller,'read_web')

		self.reactor = Reactor(self.web, self.proxy, self.manager, self.content, self.client, self.poller)

		# Only here so the introspection code can find them
		self.configuration = configuration
		self.logger = logger

		self._shutdown = False
		self._reload = False
		self._toggle_debug = False
		self._decrease_spawn_limit = False
		self._increase_spawn_limit = False
		self._refork = True

		signal.signal(signal.SIGTERM, self.sigterm)
		signal.signal(signal.SIGHUP, self.sighup)
		signal.signal(signal.SIGALRM, self.sigalrm)
		signal.signal(signal.SIGUSR1, self.sigusr1)
		signal.signal(signal.SIGUSR2, self.sigusr2)
		signal.signal(signal.SIGTRAP, self.sigtrap)


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

	def sigalrm (self,signum, frame):
		logger.info('signal','SIG ALRM received, refork request')
		self._refork = True


	def run (self):
		if self.daemon.drop_privileges():
			logger.warning('supervisor','Could not drop privileges to \'%s\' refusing to run as root' % self.daemon.user)
			logger.warning('supervisor','Set the environmemnt value USER to change the unprivileged user')
			return

		ok = self.initialise()
		if not ok:
			self._shutdown = True

		while True:
			try:
				if self._toggle_debug:
					self._toggle_debug = False
					logger.toggle()

				if self._shutdown:
					self._shutdown = False
					self.shutdown()
					break
				elif self._reload and reload_completed:
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

				# make sure we have enough workers
				self.manager.provision()
				# check for IO change with select
				self.reactor.run()

				# Quit on problems which can not be fixed (like running out of file descriptor)
				self._shutdown = not self.reactor.running

			except KeyboardInterrupt:
				logger.info('supervisor','^C received')
				self._shutdown = True

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
		s = self.proxy.listen(configuration.HOST,configuration.PORT, configuration.TIMEOUT, configuration.BACKLOG)
		ok = bool(s)
		if not s:
			logger.error('supervisor', 'Unable to listen on %s:%s' % (configuration.HOST, configuration.PORT))

		if configuration.WEB:
			s = self.web.listen('127.0.0.1',configuration.WEB, 10, 10)
			if not s:
				logger.error('supervisor', 'Unable to listen on %s:%s' % ('127.0.0.1', configuration.WEB))
				ok = False

		return ok

	def shutdown (self):
		"""terminate all the current BGP connections"""
		logger.info('supervisor','Performing shutdown')
		try:
			self.web.stop()  # accept no new web connection
			self.proxy.stop()  # accept no new proxy connections
			self.manager.stop()  # shut down redirector children
			self.content.stop() # stop downloading data
			self.client.stop() # close client connections
			self.pid.remove()
		except KeyboardInterrupt:
			logger.info('supervisor','^C received while shutting down. Exiting immediately because you insisted.')
			sys.exit()

	def reload (self):
		logger.info('supervisor','Performing reload of exaproxy %s' % configuration.VERSION ,'supervisor')
		self.manager.respawn()
