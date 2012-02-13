import time

from .worker import DNSResolver
from exaproxy.network.functions import isip

class ResolverManager(object):
	resolver_factory = DNSResolver()

	def __init__(self, poller, configuration):
		self.poller = poller
		self.configuration = configuration

		# The actual work is done in the worker
		self.worker = self.resolver_factory.createUDPClient()

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

	def cleanup(self):
		cutoff = time.time() - 2
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
					client_id, hostname, command, decision = data
					yield client_id, 'rewrite', '\0'.join(('503', 'dns.html', '', '', hostname, ''))

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
		if command == 'download':
			hostname = decision.split('\0')[0]

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
			identifier = self.worker.resolveHost(hostname)
			self.resolving[identifier] = client_id, hostname, command, decision
			self.clients[client_id] = identifier
			self.active.append((time.time(), client_id))
		else:
			identifier = None

		return identifier

	def startResolvingTCP(self, client_id, hostname, decision):
		hostname = self.extractHostname(command, decision)

		if hostname:
			worker = self.resolver_worker.createTCPClient()
			self.workers[worker.socket] = worker

			identifier, all_sent = self.worker.resolveHost(hostname)
			self.clients[client_id] = identifier
			self.active.append((time.time(), client_id))

			if all_sent:
				self.poller.addReadSocket('read_resolver', worker.socket)
				self.resolving[identifier] = client_id, hostname, command, decision
			else:
				self.poller.addWriteSocket('write_resolver', worker.socket)
				self.sending[worker.socket] = client_id, hostname, command, decision

		else:
			identifier = None

		return identifier

	def getResponse(self, sock):
		worker = self.workers.get(sock)

		if worker:
			identifier, forhost, ip, completed, newidentifier = worker.getResponse()

			data = self.resolving.pop(identifier, None)
			if data:
				client_id, hostname, command, decision = data
				self.clients.pop(client_id)

				# check to see if we received an incomplete response
				if not completed:
					worker = self.worker = self.resolver_factory.createTCPClient()
					# XXX:	this will start with a request for an A record again even if
					#	the UDP client choked only once it asked for the AAAA
					newidentifier = worker.resolveHost(hostname)
					response = None

					if newidentifier:
						self.poller.addReadSocket('read_resolver', worker.socket)
					else:
						self.poller.addWriteSocket('write_resolver', worker.socket)
						self.sending[worker.socket] = client_id, hostname, command, decision

				# check to see if the worker started a new request
				if newidentifier:
					self.resolving[identifier] = client_id, hostname, command, decision
					response = None

				# we started a new (TCP) request and have not yet completely sent it
				elif not completed:
					response = None

				# maybe we read the wrong response?
				elif forhost != hostname:
					self.resolving[identifier] = client_id, hostname, command, decision
					self.clients[client_id] = identifier
					self.active.append((time.time(), client_id))
					response = None

				# success
				elif ip is not None:
					resolved = self.resolveDecision(command, decision, ip)
					response = client_id, command, resolved

				# not found
				else:
					# XXX: 'peer' should be the peer ip
					newdecision = '\0'.join('503', 'dns.html', 'http', '', hostname, '', 'peer')
					response = client_id, 'rewrite', newdecision

			else:
				response = None

			if worker.isClosed():
				self.poller.removeReadSocket('read_resolver', sock)
				self.workers.pop(sock)

		else:
			response = None

		return response


	def continueSending(self, sock):
		"""Continue sending data over the connected TCP socket"""
		data = self.sending.get(sock)
		if data:
			client_id, hostname, command, decision = data
			worker = self.workers[sock]
			identifier = self.clients[client_id]

			res = worker.continueSending()

			if res is False: # we've sent all we need to send
				tmp = self.sending.pop(sock)
				self.resolving[identifier] = tmp

				self.poller.removeWriteSocket('write_resolver', sock)
				self.poller.addReadSocket('read_resolver', sock)
