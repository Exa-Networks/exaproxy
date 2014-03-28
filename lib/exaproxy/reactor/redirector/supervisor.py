# encoding: utf-8
"""
supervisor.py

Created by Thomas Mangin on 2011-11-29.
Copyright (c) 2011-2013  Exa Networks. All rights reserved.
"""

import os
import sys
import signal

from exaproxy.network.async import Poller
from exaproxy.util.log.writer import UsageWriter
from .manager import RedirectorManager
from .reactor import RedirectorReactor


class RedirectorSupervisor (object):
	alarm_time = 1							# regular backend work
	increase_frequency = int(5/alarm_time)	# when we add workers
	decrease_frequency = int(60/alarm_time)	# when we remove workers

	def __init__ (self, configuration, messagebox):
		self.configuration = configuration
		self.usage_writer = UsageWriter('usage', configuration.usage.destination, configuration.usage.enable)

		if configuration.debug.log:
			self.usage_writer.toggleDebug()

		self.messagebox = messagebox
		self.poller = Poller(self.configuration.daemon)

		self.manager = RedirectorManager(configuration, self.poller)

		signal.signal(signal.SIGUSR1, self.sigusr1)
		signal.signal(signal.SIGUSR2, self.sigusr2)
		signal.signal(signal.SIGSTOP, self.sigstop)
		signal.signal(signal.SIGHUP, self.sighup)
		signal.signal(signal.SIGALRM, self.sigalrm)

		self.poller.setupRead('read_request')		# requests passed from the main process
		self.poller.setupRead('read_workers')		# responses from the child processes
		self.poller.addReadSocket('read_request', messagebox.box.pipe_in)
		print 'reading input on', messagebox.box.pipe_in.fileno()

		self._increase_spawn_limit = 0
		self._decrease_spawn_limit = 0
		self._respawn = False

		# start the child processes
		self.manager.provision()

		self.reactor = RedirectorReactor(self.configuration, self.messagebox, self.manager, self.usage_writer, self.poller)
		self.running = True

	def sigusr1 (self, signum, frame):
		self._decrease_spawn_limit += 1

	def sigusr2 (self, signum, frame):
		self._increase_spawn_limit += 1

	def sigstop (self, signum, frame):
		self.running = False

	def sighup (self, signum, frame):
		self._respawn = True

	def sigalrm (self, signum, frame):
		self.reactor.running = False
		signal.setitimer(signal.ITIMER_REAL, self.alarm_time, self.alarm_time)


	def increase_spawn_limit (self):
		count = self._increase_spawn_limit
		self._increase_spawn_limit = 0

		self.manager.low += count
		self.manager.high = max(self.manager.low, self.manager.high)
		self.manager.increase(count)

	def decrease_spawn_limit (self):
		count = self._decrease_spawn_limit
		self._decrease_spawn_limit = 0

		self.manager.high = max(1, self.manager.high - count)
		self.manager.low = min(self.manager.high, self.manager.low)
		self.manager.decrease(count)


	def run (self):
		signal.setitimer(signal.ITIMER_REAL,self.alarm_time,self.alarm_time)

		count_increase = 0
		count_decrease = 0

		while self.running is True:
			count_increase = (count_increase + 1) % self.increase_frequency
			count_decrease = (count_decrease + 1) % self.decrease_frequency

			try:
				# check for IO change with select
				status = self.reactor.run()
				if status is False:
					break

				if self._increase_spawn_limit:
					self.increase_spawn_limit()

				if self._decrease_spawn_limit:
					self.decrease_spawn_limit()

				# make sure we have enough workers
				if count_increase == 0:
					self.manager.provision()

				# and every so often remove useless workers
				if count_decrease == 0:
					self.manager.deprovision()

				# check to respawn command
				if self._respawn is True:
					self._respawn = False
					self.manager.respawn()

			except:
				pass
