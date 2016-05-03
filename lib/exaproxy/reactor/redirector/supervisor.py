# encoding: utf-8
"""
supervisor.py

Created by Thomas Mangin on 2011-11-29.
Copyright (c) 2011-2013  Exa Networks. All rights reserved.
"""

import signal

from exaproxy.network.async import Poller
from exaproxy.util.log.writer import UsageWriter
from exaproxy.util.log.writer import SysLogWriter
from .manager import RedirectorManager
from .reactor import RedirectorReactor


class RedirectorSupervisor (object):
	alarm_time = 1                           # regular backend work
	increase_frequency = int(5/alarm_time)   # when we add workers
	decrease_frequency = int(60/alarm_time)  # when we remove workers

	def __init__ (self, configuration, messagebox, controlbox):
		self.configuration = configuration
		self.log_writer = SysLogWriter('log', configuration.log.destination, configuration.log.enable, level=configuration.log.level)
		self.usage_writer = UsageWriter('usage', configuration.usage.destination, configuration.usage.enable)

		if configuration.debug.log:
			self.usage_writer.toggleDebug()

		self.messagebox = messagebox
		self.controlbox = controlbox
		self.poller = Poller(self.configuration.daemon, speed=0)
		self.poller.setupRead('control')		# control messages from the main process
		self.poller.addReadSocket('control', controlbox.box.pipe_in)

		signal.signal(signal.SIGALRM, self.sigalrm)
		self._respawn = False

		# poller for the reactor
		poller = Poller(self.configuration.daemon)
		poller.setupRead('read_request')  # requests passed from the main process
		poller.setupRead('read_workers')  # responses from the child processes
		poller.setupRead('control')       # the reactor needs to yield to the supervisor
		poller.addReadSocket('read_request', messagebox.box.pipe_in)
		poller.addReadSocket('control', controlbox.box.pipe_in)

		self.manager = RedirectorManager(configuration, poller)

		# start the child processes
		self.manager.startup()

		self.reactor = RedirectorReactor(self.configuration, self.messagebox, self.manager, self.log_writer, self.usage_writer, poller)
		self.running = True

	def sigalrm (self, signum, frame):
		self.reactor.running = False
		signal.setitimer(signal.ITIMER_REAL, self.alarm_time, self.alarm_time)


	def increase_spawn_limit (self,count):
		self.manager.low += count
		self.manager.high = max(self.manager.low, self.manager.high)
		self.manager.increase(count)

	def decrease_spawn_limit (self,count):
		self.manager.high = max(1, self.manager.high - count)
		self.manager.low = min(self.manager.high, self.manager.low)
		self.manager.decrease(count)

	def sendStats (self, identifier):
		self.controlbox.respond(identifier, 'STATS', {
			'forked' : len(self.manager.worker),
			'min' :    self.manager.low,
			'max' :    self.manager.high,
			'queue' :  self.manager.queue.qsize(),
		})

	def control (self):
		status = True
		identifier, command, data = self.controlbox.receive()

		if command == 'STATS':
			self.sendStats(identifier)

		elif command == 'INCREASE':
			self.increase_spawn_limit(data[0])

		elif command == 'DECREASE':
			self.decrease_spawn_limit(data[0])

		elif command == 'RESPAWN':
			self._respawn = True

		if command == 'STOP' or not command:
			status = False

		return status

	def run (self):
		signal.setitimer(signal.ITIMER_REAL,self.alarm_time,self.alarm_time)

		count_increase = 0
		count_decrease = 0

		try:
			while self.running is True:
				count_increase = (count_increase + 1) % self.increase_frequency
				count_decrease = (count_decrease + 1) % self.decrease_frequency
	
				# check for IO change with select
				status = self.reactor.run()
				if status is False:
					break
	
	
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
	
	
				events = self.poller.poll()
				while events.get('control'):
					if not self.control():
						self.running = False
						break
	
					events = self.poller.poll()

		except KeyboardInterrupt:
			pass

		self.manager.kill_workers()
