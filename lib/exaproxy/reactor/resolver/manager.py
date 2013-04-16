import time

from .worker import DNSResolver
from exaproxy.network.functions import isip



class ResolverManager (object):
	resolverFactory = DNSResolver

	def __init__ (self, poller, configuration, max_workers):
		self.poller = poller
		self.configuration = configuration

		self.resolver_factory = self.resolverFactory(configuration)

		# The actual work is done in the worker
		self.worker = self.resolver_factory.createUDPClient()

		# All currently active clients (one UDP and many TCP)
		self.workers = {}
		self.workers[self.worker.socket] = self.worker
		self.poller.addReadSocket('read_resolver', self.worker.socket)

		# Track the clients currently expecting results
		self.clients = {}  # client_id : identifier

		# Key should be the hostname rather than the request ID?
		self.resolving = {}  # identifier, worker_id :

		# TCP workers that have not yet sent a complete request
		self.sending = {}  # sock :

		# track the current queries and when they were started
		self.active = []

		self.cache = {}
		self.cached = []

		self.max_workers = max_workers
		self.worker_count = len(self.workers)  # the UDP client

		self.waiting = []

	def cacheDestination (self, hostname, ip):
		if hostname not in self.cache:
			expire_time = time.time() + self.configuration.dns.ttl
			expire_time = expire_time - expire_time % self.configuration.dns.resolution
			latest_time, latest_hosts = self.cached[-1] if self.cached else (-1, None)

			if expire_time > latest_time:
				hosts = []
				self.cached.append((expire_time, hosts))
			else:
				hosts = latest_hosts

			self.cache[hostname] = ip
			hosts.append(hostname)

	def expireCache (self):
		# expire only one set of cache entries at a time
		if self.cached:
			current_time = time.time()
			expire_time, hosts = self.cached[0]

			if current_time >= expire_time:
				(expire_time, hosts), self.cached = self.cached[0], self.cached[1:]

				for hostname in hosts:
					self.cache.pop(hostname, None)


	def cleanup(self):
		cutoff = time.time() - self.configuration.dns.timeout
		count = 0

		for timestamp, client_id, sock in self.active:
			if timestamp > cutoff:
				break

			count += 1
			cli_data = self.clients.pop(client_id, None)
			worker = self.workers.get(sock)

			if cli_data is not None:
				w_id, identifier, active_time  = cli_data
				data = self.resolving.pop((w_id, identifier), None)
				if not data:
					data = self.sending.pop(sock, None)

				if data:
					client_id, original, hostname, command, decision = data
					yield client_id, 'rewrite', '\0'.join(('503', 'dns.html', '', '', '', hostname, 'peer'))

			if worker is not None:
				if worker is not self.worker:
					worker.close()
					self.workers.pop(sock)

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

			elif self.configuration.dns.fqdn and '.' not in hostname:
				identifier = 'not-found'
				response = None

			else:
				identifier, _ = self.worker.resolveHost(hostname)
				response = None
				active_time = time.time()

				self.resolving[(self.worker.w_id, identifier)] = client_id, hostname, hostname, command, decision
				self.clients[client_id] = (self.worker.w_id, identifier, active_time)
				self.active.append((active_time, client_id, self.worker.socket))
		else:
			identifier = None
			response = None

		return identifier, response

	def beginResolvingTCP (self, client_id, command, decision):
		if self.worker_count < self.max_workers:
			identifier = self.newTCPResolver(client_id, command, decision)
			self.worker_count += 1
		else:
			self.waiting.append((client_id, command, decision))
			identifier = None

		return identifier

	def notifyClose (self):
		paused = self.worker_count >= self.max_workers
		self.worker_count -= 1

		if paused and self.worker_count < self.max_workers:
			for _ in range(self.worker_count, self.max_workers):
				if self.waiting:
					data, self.waiting = self.waiting[0], self.waiting[1:]
					client_id, command, decision = data

					identifier = self.newTCPResolver(client_id, command, decision)
					self.worker_count += 1

	def newTCPResolver (self, client_id, command, decision):
		hostname = self.extractHostname(command, decision)

		if hostname:
			worker = self.resolver_factory.createTCPClient()
			self.workers[worker.socket] = worker

			identifier, all_sent = worker.resolveHost(hostname)
			active_time = time.time()
			self.resolving[(worker.w_id, identifier)] = client_id, hostname, hostname, command, decision
			self.clients[client_id] = (worker.w_id, identifier, active_time)
			self.active.append((active_time, client_id, self.worker.socket))

			if all_sent:
				self.poller.addReadSocket('read_resolver', worker.socket)
				self.resolving[(worker.w_id, identifier)] = client_id, hostname, hostname, command, decision
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
				data = self.resolving.pop((worker.w_id, identifier), None)

			else:
				# unable to parse response
				data = None

			if data:
				client_id, original, hostname, command, decision = data
				clidata = self.clients.pop(client_id, None)

				if completed:
					if clidata is not None:
						key = clidata[2], client_id, worker.socket
						if key in self.active:
							self.active.remove(key)

				# check to see if we received an incomplete response
				if not completed:
					newidentifier = self.beginResolvingTCP(client_id, command, decision)
					newhost = hostname
					response = None

				# check to see if the worker started a new request
				if newidentifier:
					if completed:
						active_time = time.time()
						self.resolving[(worker.w_id, newidentifier)] = client_id, original, newhost, command, decision
						self.clients[client_id] = (worker.w_id, newidentifier, active_time)
						self.active.append((active_time, client_id, worker.socket))

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
					active_time = time.time()
					self.resolving[(worker.w_id, identifier)] = client_id, original, hostname, command, decision
					self.clients[client_id] = (worker.w_id, identifier, active_time)
					self.active.append((active_time, client_id, worker.socket))
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

			if response or result is None:
				if worker is not self.worker:
					self.poller.removeReadSocket('read_resolver', sock)
					self.poller.removeWriteSocket('write_resolver', sock)
					worker.close()
					self.workers.pop(sock)
					self.notifyClose()

		else:
			response = None

		return response


	def continueSending(self, sock):
		"""Continue sending data over the connected TCP socket"""
		data = self.sending.get(sock)
		if data:
			client_id, original, hostname, command, decision = data
			worker = self.workers[sock]
			w_id, identifier, active_time = self.clients[client_id]

			res = worker.continueSending()

			if res is False: # we've sent all we need to send
				tmp = self.sending.pop(sock)
				self.resolving[(w_id, identifier)] = tmp

				self.poller.removeWriteSocket('write_resolver', sock)
				self.poller.addReadSocket('read_resolver', sock)
