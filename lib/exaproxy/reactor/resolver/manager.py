import time

from collections import deque

from .worker import DNSResolver
from exaproxy.network.functions import isip
from exaproxy.util.log.logger import Logger

class ResolverManager (object):
	resolverFactory = DNSResolver

	def __init__ (self, poller, configuration, max_workers):
		self.poller = poller
		self.configuration = configuration

		self.resolver_factory = self.resolverFactory(configuration)

		# The actual work is done in the worker
		self.worker = self.resolver_factory.createUDPClient()

		# All currently active clients (one UDP and many TCP)
		self.workers = {
			self.worker.socket: self.worker
		}
		self.poller.addReadSocket('read_resolver', self.worker.socket)

		# Track the clients currently expecting results
		self.clients = {}  # client_id : identifier

		# Key should be the hostname rather than the request ID?
		self.resolving = {}  # identifier, worker_id :

		# TCP workers that have not yet sent a complete request
		self.sending = {}  # sock :

		# Maximum number of entry we will cache (1024 DNS lookup per second !)
		# assuming 1k per entry, which is a lot, it mean 20Mb of memory
		# which at the default of 900 seconds of cache is 22 new host per seonds
		self.max_entries  = 1024*20

		# track the current queries and when they were started
		self.active = []

		self.cache = {}
		self.cached = deque()

		self.max_workers = max_workers
		self.worker_count = len(self.workers)  # the UDP client

		self.waiting = []

		self.log = Logger('resolver', configuration.log.resolver)
		self.chained = {}

	def cacheDestination (self, hostname, ip):
		if hostname not in self.cache:
			expire_time = time.time() + self.configuration.dns.ttl
			expire_time = expire_time - expire_time % 5  # group the DNS record per buckets 5 seconds
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

			if current_time >= expire_time or len(self.cache) > self.max_entries:
				expire_time, hosts = self.cached.popleft()

				for hostname in hosts:
					self.cache.pop(hostname, None)


	def cleanup(self):
		now = time.time()
		cutoff = now - self.configuration.dns.timeout
		count = 0

		for timestamp, client_id, sock in self.active:
			if timestamp > cutoff:
				break

			count += 1
			cli_data = self.clients.pop(client_id, None)
			worker = self.workers.get(sock)
			tcpudp = 'udp' if worker is self.worker else 'tcp'

			if cli_data is not None:
				w_id, identifier, active_time, resolve_count = cli_data
				data = self.resolving.pop((w_id, identifier), None)
				if not data:
					data = self.sending.pop(sock, None)

				if data:
					client_id, original, hostname, command, decision = data
					self.log.error('timeout when requesting address for %s using the %s client - attempt %s' % (hostname, tcpudp, resolve_count))

					if resolve_count < self.configuration.dns.retries and worker is self.worker:
						self.log.info('going to retransmit request for %s - attempt %s of %s' % (hostname, resolve_count+1, self.configuration.dns.retries))
						self.startResolving(client_id, command, decision, resolve_count+1, identifier=identifier)
						continue

					self.log.error('given up trying to resolve %s after %s attempts' % (hostname, self.configuration.dns.retries))
					yield client_id, 'rewrite', ('503', 'dns.html', '', '', '', hostname, 'peer')

			if worker is not None:
				if worker is not self.worker:
					worker.close()
					self.workers.pop(sock)

		if count:
			self.active = self.active[count:]

	def resolves(self, command, decision):
		if command in ('download', 'connect'):
			hostname = decision[0]
			if isip(hostname):
				res = False
			else:
				res = True
		else:
			res = False

		return res

	def extractHostname(self, command, decision):
		if command in ('download', 'connect'):
			hostname = decision[0]

		else:
			hostname = None

		return hostname

	def resolveDecision(self, command, decision, ip):
		if command in ('download', 'connect'):
			hostname, args = decision[0], decision[1:]
			newdecision = (ip,) + args
		else:
			newdecision = None

		return newdecision

	def startResolving(self, client_id, command, decision, resolve_count=1, identifier=None):
		hostname = self.extractHostname(command, decision)

		if hostname:
			# Resolution is already in our cache
			if hostname in self.cache and identifier is None:
				ip = self.cache[hostname]

				if ip is not None:
					resolved = self.resolveDecision(command, decision, ip)
					response = (client_id, command) + resolved

				else:
					response = client_id, 'rewrite', '503', 'dns.html', 'http', '', '', hostname, 'peer'

			# do not try to resolve domains which are not FQDN
			elif self.configuration.dns.fqdn and '.' not in hostname:
				identifier = None
				response = client_id, 'rewrite', '200', 'dns.html', 'http', '', '', hostname, 'peer'

			# each DNS part (between the dots) must be under 256 chars
			elif max(len(p) for p in hostname.split('.')) > 255:
				identifier = None
				self.log.info('jumbo hostname: %s' % hostname)
				response = client_id, 'rewrite', '503', 'dns.html', 'http', '', '', hostname, 'peer'
			# Lookup that DNS name
			else:
				identifier, _ = self.worker.resolveHost(hostname, identifier=identifier)
				response = None
				active_time = time.time()

				self.resolving[(self.worker.w_id, identifier)] = client_id, hostname, hostname, command, decision
				self.clients[client_id] = (self.worker.w_id, identifier, active_time, resolve_count)
				self.active.append((active_time, client_id, self.worker.socket))
		else:
			identifier = None
			response = None

		return identifier, response

	def beginResolvingTCP (self, client_id, command, decision, resolve_count):
		if self.worker_count < self.max_workers:
			identifier = self.newTCPResolver(client_id, command, decision, resolve_count)
			self.worker_count += 1
		else:
			self.waiting.append((client_id, command, decision, resolve_count))
			identifier = None

		return identifier

	def notifyClose (self):
		paused = self.worker_count >= self.max_workers
		self.worker_count -= 1

		if paused and self.worker_count < self.max_workers:
			for _ in range(self.worker_count, self.max_workers):
				if self.waiting:
					data, self.waiting = self.waiting[0], self.waiting[1:]
					client_id, command, decision, resolve_count = data

					identifier = self.newTCPResolver(client_id, command, decision, resolve_count)
					self.worker_count += 1

	def newTCPResolver (self, client_id, command, decision, resolve_count):
		hostname = self.extractHostname(command, decision)

		if hostname:
			worker = self.resolver_factory.createTCPClient()
			self.workers[worker.socket] = worker

			identifier, all_sent = worker.resolveHost(hostname)
			active_time = time.time()
			self.resolving[(worker.w_id, identifier)] = client_id, hostname, hostname, command, decision
			self.clients[client_id] = (worker.w_id, identifier, active_time, resolve_count)
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
			result = worker.getResponse(self.chained)

			if result:
				identifier, forhost, ip, completed, newidentifier, newhost, newcomplete = result
				data = self.resolving.pop((worker.w_id, identifier), None)

				chain_count = self.chained.pop(identifier, 0)
				if newidentifier:
					self.chained[newidentifier] = chain_count + 1

				if not data:
					self.log.info('ignoring response for %s (%s) with identifier %s' % (forhost, ip, identifier))

			else:
				# unable to parse response
				self.log.error('unable to parse response')
				data = None

			if data:
				client_id, original, hostname, command, decision = data
				clidata = self.clients.pop(client_id, None)

				if identifier is not None:
					if clidata is not None:
						key = clidata[2], client_id, worker.socket
						if key in self.active:
							self.active.remove(key)

				# check to see if we received an incomplete response
				if not completed:
					newidentifier = self.beginResolvingTCP(client_id, command, decision, 1)
					newhost = hostname
					response = None

				# check to see if the worker started a new request
				if newidentifier:
					response = None

					if completed:
						active_time = time.time()
						self.resolving[(worker.w_id, newidentifier)] = client_id, original, newhost, command, decision
						self.clients[client_id] = (worker.w_id, newidentifier, active_time, 1)
						self.active.append((active_time, client_id, worker.socket))

					if completed and newcomplete:
						self.poller.addReadSocket('read_resolver', worker.socket)

					elif completed and not newcomplete:
						self.poller.addWriteSocket('write_resolver', worker.socket)
						self.sending[worker.socket] = client_id, original, hostname, command, decision

				# we just started a new (TCP) request and have not yet completely sent it
				# make sure we still know who the request is for
				elif not completed:
					response = None

				# maybe we read the wrong response?
				elif forhost != hostname:
					_, _, _, resolve_count = clidata
					active_time = time.time()
					self.resolving[(worker.w_id, identifier)] = client_id, original, hostname, command, decision
					self.clients[client_id] = (worker.w_id, identifier, active_time, resolve_count)
					self.active.append((active_time, client_id, worker.socket))
					response = None

				# success
				elif ip is not None:
					resolved = self.resolveDecision(command, decision, ip)
					response = (client_id, command) + resolved
					self.cacheDestination(original, ip)

				# not found
				else:
					response = client_id, 'rewrite', '503', 'dns.html', 'http', '', '', hostname, 'peer'
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
		else:
			client_id, original, hostname, command, decision = None, None, None, None, None

		worker = self.workers[sock]
		res = worker.continueSending()

		if res is False: # we've sent all we need to send
			self.poller.removeWriteSocket('write_resolver', sock)

			if client_id in self.clients:
				w_id, identifier, active_time, resolve_count = self.clients[client_id]
				tmp = self.sending.pop(sock)
				self.resolving[(w_id, identifier)] = tmp
				self.poller.addReadSocket('read_resolver', sock)

			else:
				self.log.error('could not find client for dns request for %s. request is being left to timeout.' % str(hostname))
