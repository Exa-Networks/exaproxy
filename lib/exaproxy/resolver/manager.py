from .worker import DNSResolver

class ResolverManager(object):
	request_factory = DNSResolver()

	def __init__(self, configuration, poller):
		self.configuration = configuration
		self.poller = poller

		# The actual work is done in the worker
		self.worker = self.resolver_factory.createUDPWorker()

		# All currently active clients (UDP and TCP)
		self.workers = {}
		self.workers[self.worker.socket] = self.worker
                self.poller.addReadSocket('read_resolvers', self.worker.socket)

		# Key should be the hostname rather than the request ID?
		self.resolving = {}

	def startResolving(self, client_id, hostname, decision):
		identifier = self.worker.resolveHost(hostname)
		self.resolving.setdefault(identifier, []).append(client_id, hostname, decision)
		self.clients[client_id] = identifier

		return identifier

	def startResolvingTCP(self, client_id, hostname, decision):
		worker = self.resolver_worker.createTCPWorker()
		self.workers[worker.socket] = worker
		self.poller.addReadSocket('read_resolvers', worker.socket)

		identifier = self.worker.resolveHost(hostname)
		self.resolving[identifier] = client_id, hostname, decision
		self.clients[client_id] = identifier

		return identifier

	def getResponse(self, sock):
		worker = self.workers.get(sock)

		if worker:
			identifier, forhost, ip, completed, newidentifier = worker.getResponse()

			data = self.resolving.pop(identifier, None)
			if data:
				client_id, hostname, decision = data
				self.clients.pop(client_id)

				# check to see if we received an incomplete response
				if not completed:
					newidentifier = self.startResolvingTCP(client_id, hostname, decision)
					response = None

				# check to see if the worker started a new request
				elif newidentifier:
					self.resolving[identifier] = client_id, hostname, decision
					response = None

				# maybe we read the wrong response?
				elif forhost != hostname:
					self.resolving[identifier] = client_id, hostname, decision
					self.clients[client_id] = identifier
					response = None

				# success
				elif ip is not None:
					response = client_id, hostname, decision, ip

				# not found
				else:
					# XXX: 'peer' should be the peer ip
					decision = '\0'.join('rewrite', '503', 'dns.html', 'http', '', hostname, '', 'peer')
					response = client_id, hostname, decision, ip

			else:
				response = None

			if worker.isClosed():
				self.poller.removeReadSocket('read_resolvers', sock)
				self.workers.pop(sock)

		else:
			response = None

		return response
