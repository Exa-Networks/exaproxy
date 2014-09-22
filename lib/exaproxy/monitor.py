# encoding: utf-8
"""
monitor.py

Created by Thomas Mangin on 2012-02-05.
Copyright (c) 2011-2013 Exa Networks. All rights reserved.
"""

from collections import deque

class _Container (object):
	def __init__ (self,supervisor):
		self.supervisor = supervisor

class Monitor (object):
	nb_recorded = 60

	def __init__(self,supervisor):
		self._supervisor = supervisor
		self._container = _Container(supervisor)
		self.seconds = deque()
		self.minutes = deque()

	def zero (self, stats):
		if stats:
			self.seconds.append(stats)
			self.minutes.append(stats)

		return bool(stats)

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

		return {
			'exaproxy.debug.log' : bool(conf.debug.log),
			'exaproxy.debug.pdb' : bool(conf.debug.pdb),
			'exaproxy.debug.memory' : conf.debug.memory,
			'exaproxy.daemon.deamonize' : conf.daemon.daemonize,
			'exaproxy.daemon.identifier' : conf.daemon.identifier,
			'exaproxy.daemon.pidfile' : conf.daemon.pidfile,
			'exaproxy.daemon.sleep' : conf.daemon.speed,
			'exaproxy.profile.enable' : conf.profile.enable,
			'exaproxy.profile.destination' : conf.profile.destination,
			'exaproxy.dns.fqdn' : conf.dns.fqdn,
			'exaproxy.dns.resolver' : conf.dns.resolver,
			'exaproxy.dns.timeout' : conf.dns.timeout,
			'exaproxy.dns.ttl' : conf.dns.ttl,
			'exaproxy.daemon.user' : conf.daemon.user,
			'exaproxy.daemon.reactor' : conf.daemon.reactor,
			'exaproxy.log.level.daemon' : conf.log.daemon,
			'exaproxy.log.level.supervisor' : conf.log.supervisor,
			'exaproxy.log.level.signal' : conf.log.signal,
			'exaproxy.log.level.worker' : conf.log.worker,
			'exaproxy.log.level.server' : conf.log.server,
			'exaproxy.log.level.manager' : conf.log.manager,
			'exaproxy.log.level.client' : conf.log.client,
			'exaproxy.log.level.download' : conf.log.download,
			'exaproxy.log.level.http' : conf.log.http,
			'exaproxy.log.level.configuration' : conf.log.configuration,
			'exaproxy.log.level.web' : conf.log.web,
			'exaproxy.tcp4.host' : conf.tcp4.host,
			'exaproxy.tcp4.port' : conf.tcp4.port,
			'exaproxy.tcp4.backlog' : conf.tcp4.backlog,
			'exaproxy.tcp4.timeout' : conf.tcp4.timeout,
			'exaproxy.tcp4.listen' : conf.tcp4.listen,
			'exaproxy.tcp4.out' : conf.tcp4.out,
			'exaproxy.tcp4.bind' : conf.tcp4.bind,
			'exaproxy.tcp6.host' : conf.tcp6.host,
			'exaproxy.tcp6.port' : conf.tcp6.port,
			'exaproxy.tcp6.backlog' : conf.tcp6.backlog,
			'exaproxy.tcp6.timeout' : conf.tcp6.timeout,
			'exaproxy.tcp6.listen' : conf.tcp6.listen,
			'exaproxy.tcp6.out' : conf.tcp6.out,
			'exaproxy.tcp6.bind' : conf.tcp6.bind,
			'exaproxy.http.connect' : conf.http.allow_connect,
			'exaproxy.http.connections' : conf.http.connections,
			'exaproxy.http.forward' : conf.http.forward,
			'exaproxy.http.transparent' : conf.http.transparent,
			'exaproxy.http.extensions' : ' '.join(str (_) for _ in conf.http.extensions),
			'exaproxy.proxy.version' : conf.proxy.version,
			'exaproxy.redirector.enable' : conf.redirector.enable,
			'exaproxy.redirector.protocol' : conf.redirector.protocol,
			'exaproxy.redirector.program' : conf.redirector.program,
			'exaproxy.redirector.minimum' : conf.redirector.minimum,
			'exaproxy.redirector.maximum' : conf.redirector.maximum,
			'exaproxy.security.local' : ' '.join(str(_) for _ in conf.security.local),
			'exaproxy.security.connect' : ' '.join(str(_) for _ in conf.security.connect),
			'exaproxy.usage.destination' : conf.usage.destination,
			'exaproxy.usage.enable' : conf.usage.enable,
			'exaproxy.web.enable' : conf.web.enable,
			'exaproxy.web.host' : '127.0.0.1',
			'exaproxy.web.port' : conf.web.port,
			'exaproxy.web.debug' : conf.web.debug,
		}

	def statistics (self, stats):
		content = self._supervisor.content
		client = self._supervisor.client
		reactor = self._supervisor.reactor

		if not stats:
			return {}

		return {
			'pid.saved' : self._supervisor.pid._saved_pid,
			'processes.forked' : stats['forked'],
			'processes.min' : stats['min'],
			'processes.max' : stats['max'],
			'clients.silent' : len(client.norequest),
			'clients.speaking' : len(client.byname),
			'clients.requests' : client.total_requested,
			'servers.opening' : len(content.opening),
			'servers.established' : len(content.established),
			'transfer.client4' : client.total_sent4,
			'transfer.client6' : client.total_sent6,
			'transfer.client' : client.total_sent4 + client.total_sent6,
			'transfer.content4' : content.total_sent4,
			'transfer.content6' : content.total_sent6,
			'transfer.content' : content.total_sent4 + content.total_sent6,
			'load.loops' : reactor.nb_loops,
			'load.events' : reactor.nb_events,
			'queue.size' : stats['queue'],
		}

	def second (self, stats):
		self.seconds.append(stats)

		if len(self.seconds) > self.nb_recorded:
			self.seconds.popleft()

		return True

	def minute (self, stats):
		self.minutes.append(stats)

		if len(self.minutes) > self.nb_recorded:
			self.minutes.popleft()

		return True
