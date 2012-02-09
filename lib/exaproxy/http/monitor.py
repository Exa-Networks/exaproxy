#!/usr/bin/env python
# encoding: utf-8
"""
monitor.py

Created by Thomas Mangin on 2012-02-05.
Copyright (c) 2012 Exa Networks. All rights reserved.
"""

class _Container (object):
	def __init__ (self,supervisor):
		self.supervisor = supervisor

class Monitor (object):
	
	def __init__(self,supervisor):
		self._supervisor = supervisor
		self._container = _Container(supervisor)
		self.history = []

	def introspection (self,objects):
		obj = self._container
		ks = [_ for _ in dir(obj) if not _.startswith('__') and not _.endswith('__')]

		for key in objects:
			if not key in ks:
				raise StopIteration()
			obj = getattr(obj,key)
			ks = [_ for _ in dir(obj) if not _.startswith('__') and not _.endswith('__')]

		for k in ks:
			value = str(getattr(obj,k))
			if value.startswith('<bound method'):
				continue
			if value.startswith('<function '):
				continue
			yield k, value

	def configuration (self):
		conf = self._supervisor.configuration
		content = self._supervisor.content
		client = self._supervisor.client
		logger = self._supervisor.logger
		manager = self._supervisor.manager
		reactor = self._supervisor.reactor

		return {
			'configuration.global.deamonize' : str(bool(conf.DAEMONIZE)),
			'configuration.global.debugging' : str(bool(logger.pdb)),
			'configuration.global.pidfile' : str(conf.PID),
			'configuration.global.profiled' : str(bool(conf.PROFILE)),
			'configuration.global.resolver' : str(conf.RESOLV),
			'configuration.global.user' : str(conf.USER),
			'configuration.global.version' : '%s %s' % (conf.NAME,str(conf.VERSION)),
			'configuration.logger.level.daemon' : str(bool(logger.status['daemon'])),
			'configuration.logger.level.main' : str(bool(logger.status['main'])),
			'configuration.logger.level.supervisor' : str(bool(logger.status['supervisor'])),
			'configuration.logger.level.signal' : str(bool(logger.status['signal'])),
			'configuration.logger.level.worker' : str(bool(logger.status['worker'])),
			'configuration.logger.level.server' : str(bool(logger.status['server'])),
			'configuration.logger.level.manager' : str(bool(logger.status['manager'])),
			'configuration.logger.level.client' : str(bool(logger.status['client'])),
			'configuration.logger.level.download' : str(bool(logger.status['download'])),
			'configuration.logger.level.http' : str(bool(logger.status['http'])),
			'configuration.logger.level.configuration' : str(bool(logger.status['configuration'])),
			'configuration.proxy.tcp.host' : str(conf.HOST),
			'configuration.proxy.tcp.port' : str(conf.PORT),
			'configuration.proxy.tcp.backlog' : str(conf.BACKLOG),
			'configuration.proxy.tcp.sleep' : str(conf.SPEED),
			'configuration.proxy.tcp.timeout' : str(conf.TIMEOUT),
			'configuration.proxy.http.connect' : str(conf.CONNECT),
			'configuration.proxy.http.x-forwarded-for' : str(conf.XFF),
			'configuration.global.deamonize' : str(conf.DAEMONIZE),
			'configuration.processes.min' : str(conf.MIN_WORK),
			'configuration.processes.max' : str(conf.MAX_WORK),
			'configuration.processes.program' : str(conf.PROGRAM),
			'configuration.web.host' : '127.0.0.1',
			'configuration.web.port' : str(conf.WEB),
		}

	def statistics (self):
		conf = self._supervisor.configuration
		content = self._supervisor.content
		client = self._supervisor.client
		logger = self._supervisor.logger
		manager = self._supervisor.manager
		reactor = self._supervisor.reactor

		return {
			'running.pid.saved' : str(self._supervisor.pid._saved_pid),
			'running.processes.forked' : str(len(manager.worker)),
			'running.processes.min' : str(manager.low),
			'running.processes.max' : str(manager.high),
			'running.proxy.clients.number': str(len(client.byname)),
			'running.proxy.download.opening': str(len(content.opening)),
			'running.proxy.download.established': str(len(content.established)),
			'running.proxy.download' : str(len(content.byclientid)),
			'running.exiting' : str(bool(not reactor.running or self._supervisor._refork))
		}

	def record (self):
		self.history.append(self.statistics())
		self.history = self.history[-60:]