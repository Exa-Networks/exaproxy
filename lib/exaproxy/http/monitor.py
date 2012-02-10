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
			'configuration.global.debugging' : str(bool(logger.pdb)),
			'configuration.daemon.deamonize' : str(conf.daemon.daemonise),
			'configuration.daemon.pidfile' : str(conf.daemon.pidfile),
			'configuration.profile.enabled' : str(conf.profile.enabled),
			'configuration.profile.destination' : str(conf.profile.destination),
			'configuration.daemon.resolver' : str(conf.daemon.resolver),
			'configuration.daemon.user' : str(conf.daemon.user),
			'configuration.global.version' : '%s %s' % (conf.proxy.name,str(conf.proxy.version)),
			'configuration.logger.level.daemon' : str(conf.logger.daemon),
			'configuration.logger.level.main' : str(conf.logger.main),
			'configuration.logger.level.supervisor' : str(conf.logger.supervisor),
			'configuration.logger.level.signal' : str(conf.logger.signal),
			'configuration.logger.level.worker' : str(conf.logger.worker),
			'configuration.logger.level.server' : str(conf.logger.server),
			'configuration.logger.level.manager' : str(conf.logger.manager),
			'configuration.logger.level.client' : str(conf.logger.client),
			'configuration.logger.level.download' : str(conf.logger.download),
			'configuration.logger.level.http' : str(conf.logger.http),
			'configuration.logger.level.configuration' : str(conf.logger.configuration),
			'configuration.tcp.host' : str(conf.tcp.host),
			'configuration.tcp.port' : str(conf.tcp.port),
			'configuration.tcp.backlog' : str(conf.tcp.backlog),
			'configuration.tcp.sleep' : str(conf.tcp.speed),
			'configuration.tcp.timeout' : str(conf.tcp.timeout),
			'configuration.http.connect' : str(conf.http.allow_connect),
			'configuration.http.x-forwarded-for' : str(conf.http.x_forwarded_for),
			'configuration.redirector.minimum' : str(conf.redirector.minimum),
			'configuration.redirector.maximum' : str(conf.redirector.maximum),
			'configuration.redirector.program' : str(conf.redirector.program),
			'configuration.redirector.timeout' : str(conf.redirector.timeout),
			'configuration.web.enabled' : str(conf.web.enabled),
			'configuration.web.host' : '127.0.0.1',
			'configuration.web.port' : str(conf.web.port),
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