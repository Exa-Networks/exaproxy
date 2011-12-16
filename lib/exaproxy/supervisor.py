#!/usr/bin/env python
# encoding: utf-8
"""
supervisor.py

Created by Thomas Mangin on 2011-11-29.
Copyright (c) 2011 Exa Networks. All rights reserved.
"""

import os
import signal
from Queue import Queue

from .pid import PID
from .daemon import Daemon
from .classify.manager import Manager
from .server import Server,SelectError
from .download import Download

from .logger import Logger
logger = Logger()

from .configuration import Configuration
configuration = Configuration()

class Supervisor(object):
	# import os
	# clear = [hex(ord(c)) for c in os.popen('clear').read()]
	clear = ''.join([chr(int(c,16)) for c in ['0x1b', '0x5b', '0x48', '0x1b', '0x5b', '0x32', '0x4a']])

	def __init__ (self):

		self.pid = PID()
		self.daemon = Daemon()

		request_box = Queue()
		
		# XXX : Should manager and Download moved into server ?
		self.manager = Manager(request_box,configuration.PROGRAM)
		self.download = Download()
		self.server = Server(self.download,self.manager,request_box,'127.0.0.1',3128,5,200,configuration.SPEED)

		self._shutdown = False
		self._reload = False

		signal.signal(signal.SIGTERM, self.sigterm)
		signal.signal(signal.SIGHUP, self.sighup)
		signal.signal(signal.SIGALRM, self.sigalrm)

		self.increase_spawn_limit = False

		
	def sigterm (self,signum, frame):
		logger.supervisor('SIG TERM received')
		self._shutdown = True

	def sighup (self,signum, frame):
		logger.supervisor('SIG HUP received')
		self._reload = True

	def sigalrm (self,signum, frame):
		logger.supervisor('SIG ALRM received')
		self.increase_spawn_limit = True

	def run (self):
		if self.daemon.drop_privileges():
			logger.supervisor('Could not drop privileges to \'%s\' refusing to run as root' % self.daemon.user)
			logger.supervisor('Set the environmemnt value USER to change the unprivileged user')
			return

		self.initialise()

		while True:
			try:
				if self._shutdown:
					self._shutdown = False
					self.shutdown()
					break
				elif self._reload and reload_completed:
					self._reload = False
					self.reload()

				if self.increase_spawn_limit:
					if self.manager.low == self.manager.high: self.manager.high += 1
					self.manager.low = min(self.manager.high,self.manager.low+1)
					self.increase_spawn_limit = False

				# make sure we have enough workers
				self.manager.provision()
				# check for IO change with select
				self.server.run()

				# Quit on problems which can not be fixed (like running out of file descriptor)
				self._shutdown = not self.server.running

			except KeyboardInterrupt:
				logger.supervisor('^C received')
				self._shutdown = True
			except SelectError:
				logger.supervisor('problem with the network')
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
		# start our threads (a normal class)
		self.manager.start()
		# only start listening once we know we were able to fork our worker processes
		self.server.start()

	def shutdown (self):
		"""terminate all the current BGP connections"""
		logger.info('Performing shutdown','supervisor')
		self.server.stop()
		self.manager.stop()
		self.download.stop()
		self.pid.remove()

	def reload (self):
		logger.info('Performing reload of exaproxy %s' % configuration.VERSION ,'supervisor')
		self.manager.respawn()
