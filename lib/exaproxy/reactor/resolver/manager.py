import time

from .worker import DNSResolver
from exaproxy.network.functions import isip

class ResolverManager(object):
	resolver_factory = DNSResolver()

	def __init__(self, poller, configuration):
		self.poller = poller
		self.configuration = configuration # needed when creating new resolver instances
		self.resolv = configuration.dns.resolver
		self.timeout = configuration.dns.timeout

		# The actual work is done in the worker
		self.worker = self.resolver_factory.createUDPClient(configuration, self.resolv)

		# All currently active clients (UDP and TCP)
		self.workers = {}
		self.workers[self.worker.socket] = self.worker
                self.poller.addReadSocket('read_resolver', self.worker.socket)

		# Track the clients currently expecting results
		self.clients = {}

		# Key should be the hostname rather than the request ID?
		self.resolving = {}

		# TCP workers that have not yet sent a complete request
		self.sending = {}

		# track the current queries and when they were started
		self.active = []

		self.cache = {}
		self.cached = []

	def cacheDestination(self, hostname, ip):
		if hostname not in self.cache:
			self.cache[hostname] = ip
			self.cached.append((time.time(), hostname))

	def expireCache(self):
		if not self.cached:
			return

		count = len(self.cached)
		stop = min(count, self.configuration.dns.expire)
		position = stop-1

		cutoff = time.time() - self.configuration.dns.ttl

		while position > 10:
			timestamp, hostname = self.cached[position]
			if timestamp > cutoff:
				break

			position = int(position/1.3)
		else:
			position = 0

		for timestamp, hostname in self.cached[position:stop]:
			if timestamp > cutoff:
				break

			position += 1

			self.cache.pop(hostname, None)

		if position:
			self.cached = self.cached[position:]
			

	def cleanup(self):
		cutoff = time.time() - self.timeout
		count = 0

		for timestamp, client_id in self.active:
			if timestamp > cutoff:
				break

			count += 1
			identifier = self.clients.get(client_id)

			if identifier is not None:
				data = self.resolving.pop(identifier, None)
				if not data:
					data = self.sending.pop(identifier, None)

				if data:
					client_id, original, hostname, command, decision = data
					yield client_id, 'rewrite', '\0'.join(('503', 'dns.html', '', '', '', hostname, 'peer'))

		if count:
			self.active = self.active[count:]

	def resolves(self, command, decision):
		if command in ('download', 'connect'):
			hostname = decision.split('\0')[0]
			if isip(hostname):
				res = False
			else:
				res = True
		else:
			res = False

		return res

	def extractHostname(self, command, decision):
		data = decision.split('\0')

		if command == 'download':
			hostname = data[0]

		elif command == 'connect':
			hostname = decision.split('\0')[0]

		else:
			hostname = None

		return hostname

	def resolveDecision(self, command, decision, ip):
		if command in ('download', 'connect'):
			hostname, args = decision.split('\0', 1)
			newdecision = '\0'.join((ip, args))
		else:
			newdecision = None

		return newdecision

	def startResolving(self, client_id, command, decision):
		hostname = self.extractHostname(command, decision)

		if hostname:
			if hostname in self.cache:
				identifier = None
				ip = self.cache[hostname]

				if ip is not None:
					resolved = self.resolveDecision(command, decision, ip)
					response = client_id, command, resolved

				else:
					newdecision = '\0'.join(('503', 'dns.html', 'http', '', '', hostname, 'peer'))
					response = client_id, 'rewrite', newdecision

			else:
				identifier, _ = self.worker.resolveHost(hostname)
				response = None
				self.resolving[identifier] = client_id, hostname, hostname, command, decision
				self.clients[client_id] = identifier
				self.active.append((time.time(), client_id))
		else:
			identifier = None
			response = None

		return identifier, response

	def startResolvingTCP(self, client_id, command, decision):
		hostname = self.extractHostname(command, decision)

		if hostname:
			worker = self.resolver_factory.createTCPClient(self.configuration, self.resolv)
			self.workers[worker.socket] = worker

			identifier, all_sent = worker.resolveHost(hostname)
			self.resolving[identifier] = client_id, hostname, hostname, command, decision
			self.clients[client_id] = identifier
			self.active.append((time.time(), client_id))

			if all_sent:
				self.poller.addReadSocket('read_resolver', worker.socket)
				self.resolving[identifier] = client_id, hostname, hostname, command, decision
			else:
				self.poller.addWriteSocket('write_resolver', worker.socket)
				self.sending[worker.socket] = client_id, hostname, hostname, command, decision

		else:
			identifier = None

		return identifier

	def getResponse(self, sock):
		worker = self.workers.get(sock)

		if worker:
			result = worker.getResponse()

			if result:
				identifier, forhost, ip, completed, newidentifier, newhost, newcomplete = result
				data = self.resolving.pop(identifier, None)
			else:
				# unable to parse response
				data = None

			if data:
				client_id, original, hostname, command, decision = data
				self.clients.pop(client_id, None)

				# check to see if we received an incomplete response
				if not completed:
					newidentifier = self.startResolvingTCP(client_id, command, decision)
					newhost = hostname
					response = None

				# check to see if the worker started a new request
				if newidentifier:
					self.resolving[newidentifier] = client_id, original, newhost, command, decision
					self.clients[client_id] = newidentifier
					response = None

					if completed and newcomplete:
						self.poller.addReadSocket('read_resolver', worker.socket)
					elif completed and not newcomplete:
						self.poller.addWriteSocket('write_resolver', worker.socket)
						self.sending[worker.socket] = client_id, original, hostname, command, decision

				# we just started a new (TCP) request and have not yet completely sent it
				elif not completed:
					response = None

				# maybe we read the wrong response?
				elif forhost != hostname:
					self.resolving[identifier] = client_id, original, hostname, command, decision
					self.clients[client_id] = identifier
					self.active.append((time.time(), client_id))
					response = None

				# success
				elif ip is not None:
					resolved = self.resolveDecision(command, decision, ip)
					response = client_id, command, resolved
					self.cacheDestination(original, ip)

				# not found
				else:
					newdecision = '\0'.join(('503', 'dns.html', 'http', '', '', hostname, 'peer'))
					response = client_id, 'rewrite', newdecision
					#self.cacheDestination(original, ip)
			else:
				response = None

			if response:
				if worker.shouldClose():
					self.poller.removeReadSocket('read_resolver', sock)
					self.poller.removeWriteSocket('write_resolver', sock)
					worker.close()
					self.workers.pop(sock)

		else:
			response = None

		return response


	def continueSending(self, sock):
		"""Continue sending data over the connected TCP socket"""
		data = self.sending.get(sock)
		if data:
			client_id, original, hostname, command, decision = data
			worker = self.workers[sock]
			identifier = self.clients[client_id]

			res = worker.continueSending()

			if res is False: # we've sent all we need to send
				tmp = self.sending.pop(sock)
				self.resolving[identifier] = tmp

				self.poller.removeWriteSocket('write_resolver', sock)
				self.poller.addReadSocket('read_resolver', sock)
