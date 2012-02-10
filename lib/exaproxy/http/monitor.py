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
			'exaproxy.global.debugging' : str(bool(logger.pdb)),
			'exaproxy.daemon.deamonize' : str(conf.daemon.daemonise),
			'exaproxy.daemon.pidfile' : str(conf.daemon.pidfile),
			'exaproxy.profile.enabled' : str(conf.profile.enabled),
			'exaproxy.profile.destination' : str(conf.profile.destination),
			'exaproxy.daemon.resolver' : str(conf.daemon.resolver),
			'exaproxy.daemon.user' : str(conf.daemon.user),
			'exaproxy.global.version' : '%s %s' % (conf.proxy.name,str(conf.proxy.version)),
			'exaproxy.logger.level.daemon' : str(conf.logger.daemon),
			'exaproxy.logger.level.main' : str(conf.logger.main),
			'exaproxy.logger.level.supervisor' : str(conf.logger.supervisor),
			'exaproxy.logger.level.signal' : str(conf.logger.signal),
			'exaproxy.logger.level.worker' : str(conf.logger.worker),
			'exaproxy.logger.level.server' : str(conf.logger.server),
			'exaproxy.logger.level.manager' : str(conf.logger.manager),
			'exaproxy.logger.level.client' : str(conf.logger.client),
			'exaproxy.logger.level.download' : str(conf.logger.download),
			'exaproxy.logger.level.http' : str(conf.logger.http),
			'exaproxy.logger.level.configuration' : str(conf.logger.configuration),
			'exaproxy.tcp.host' : str(conf.tcp.host),
			'exaproxy.tcp.port' : str(conf.tcp.port),
			'exaproxy.tcp.backlog' : str(conf.tcp.backlog),
			'exaproxy.tcp.sleep' : str(conf.tcp.speed),
			'exaproxy.tcp.timeout' : str(conf.tcp.timeout),
			'exaproxy.http.connect' : str(conf.http.allow_connect),
			'exaproxy.http.x-forwarded-for' : str(conf.http.x_forwarded_for),
			'exaproxy.redirector.minimum' : str(conf.redirector.minimum),
			'exaproxy.redirector.maximum' : str(conf.redirector.maximum),
			'exaproxy.redirector.program' : str(conf.redirector.program),
			'exaproxy.redirector.timeout' : str(conf.redirector.timeout),
			'exaproxy.web.enabled' : str(conf.web.enabled),
			'exaproxy.web.host' : '127.0.0.1',
			'exaproxy.web.port' : str(conf.web.port),
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