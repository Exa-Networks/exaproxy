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
	nb_recorded = 60

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
			'exaproxy.daemon.sleep' : str(conf.daemon.speed),
			'exaproxy.profile.enable' : str(conf.profile.enable),
			'exaproxy.profile.destination' : str(conf.profile.destination),
			'exaproxy.dns.resolver' : str(conf.dns.resolver),
			'exaproxy.dns.timeout' : str(conf.dns.timeout),
#			'exaproxy.dns.force-ttl' : str(conf.dns.force_ttl),
			'exaproxy.dns.ttl' : str(conf.dns.ttl),
			'exaproxy.dns.expire' : str(conf.dns.expire),
			'exaproxy.daemon.user' : str(conf.daemon.user),
			'exaproxy.daemon.reactor' : str(conf.daemon.reactor),
			'exaproxy.global.version' : '%s %s' % (conf.proxy.name,str(conf.proxy.version)),
			'exaproxy.logger.level.daemon' : str(conf.logger.daemon),
			'exaproxy.logger.level.supervisor' : str(conf.logger.supervisor),
			'exaproxy.logger.level.signal' : str(conf.logger.signal),
			'exaproxy.logger.level.worker' : str(conf.logger.worker),
			'exaproxy.logger.level.server' : str(conf.logger.server),
			'exaproxy.logger.level.manager' : str(conf.logger.manager),
			'exaproxy.logger.level.client' : str(conf.logger.client),
			'exaproxy.logger.level.download' : str(conf.logger.download),
			'exaproxy.logger.level.http' : str(conf.logger.http),
			'exaproxy.logger.level.configuration' : str(conf.logger.configuration),
			'exaproxy.tcp4.host' : str(conf.tcp4.host),
			'exaproxy.tcp4.port' : str(conf.tcp4.port),
			'exaproxy.tcp4.backlog' : str(conf.tcp4.backlog),
			'exaproxy.tcp4.timeout' : str(conf.tcp4.timeout),
			'exaproxy.tcp4.listen' : str(conf.tcp4.listen),
			'exaproxy.tcp4.out' : str(conf.tcp4.out),
			'exaproxy.tcp6.host' : str(conf.tcp6.host),
			'exaproxy.tcp6.port' : str(conf.tcp6.port),
			'exaproxy.tcp6.backlog' : str(conf.tcp6.backlog),
			'exaproxy.tcp6.timeout' : str(conf.tcp6.timeout),
			'exaproxy.tcp6.listen' : str(conf.tcp6.listen),
			'exaproxy.tcp6.out' : str(conf.tcp6.out),
			'exaproxy.http.connect' : str(conf.http.allow_connect),
			'exaproxy.http.x-forwarded-for' : str(conf.http.x_forwarded_for),
			'exaproxy.http.transparent' : str(conf.http.transparent),
			'exaproxy.http.extensions' : ' '.join(conf.http.extensions),
			'exaproxy.redirector.enable' : str(conf.redirector.enable),
			'exaproxy.redirector.protocol' : str(conf.redirector.protocol),
			'exaproxy.redirector.program' : str(conf.redirector.program),
			'exaproxy.redirector.minimum' : str(conf.redirector.minimum),
			'exaproxy.redirector.maximum' : str(conf.redirector.maximum),
#			'exaproxy.redirector.timeout' : str(conf.redirector.timeout),
			'exaproxy.web.enable' : str(conf.web.enable),
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
			'running.processes.min' : manager.low,
			'running.processes.max' : manager.high,
			'running.proxy.clients.number': len(client.byname),
			'running.proxy.download.opening': len(content.opening),
			'running.proxy.download.established': len(content.established),
			'running.proxy.download' : len(content.byclientid),
			'running.exiting' : bool(not reactor.running or self._supervisor._refork),
			'running.transfer.request' : client.total_sent,
			'running.transfer.download' : content.total_sent,
			'running.load.loops' : reactor.nb_loops,
			'running.load.events' : reactor.nb_events,
		}

	def record (self):
		self.history.append(self.statistics())
		self.history = self.history[-self.nb_recorded:]
