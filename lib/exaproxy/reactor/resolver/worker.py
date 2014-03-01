import random
import socket

from exaproxy.dns.factory import DNSPacketFactory
from exaproxy.network.functions import connect
from exaproxy.network.functions import errno_block


def next_identifier():
	def cycle_identifiers():
		while True:
			for identifier in xrange(0xffff):
				yield identifier

	return cycle_identifiers().next




class DNSClient (object):
	extended = False

	def __init__(self, w_id, dns_factory, configuration, servers, port=53):
		self.w_id = w_id
		self.dns_factory = dns_factory
		self.configuration = configuration
		self.servers = servers
		self.port = port

		self.next_identifier = next_identifier()
		self.socket = self.startConnecting()

	def startConnecting (self):
		return None

	@property
	def server(self):
		return random.choice(self.servers)

	def resolveHost(self, hostname, qtype=None, identifier=None):
		"""Retrieve an A or AAAA entry for the requested hostname"""

		if qtype is None:
			if self.configuration.tcp4.out:
				qtype = 'A'
			else:
				qtype = 'AAAA'

		# create an A request ready to send on the wire
		identifier = identifier if identifier is not None else self.next_identifier()
		request_s = self.dns_factory.createRequestString(identifier, qtype, hostname)

		# and send it over the wire
		try:
			if request_s:
				self.socket.sendto(request_s, (self.server, self.port))
		except IOError, e:
			pass

		return identifier, True

	def readResponse (self):
		response_s, peer = self.socket.recvfrom(65535)
		return response_s

	def getResponse(self, chained={}):
		"""Read a response from the wire and return the desired result if present"""

		# We may need to make another query
		newidentifier = None
		newcomplete = True
		newhost = None

		# Read the response from the wire
		response_s = self.readResponse()

		if response_s is None:
			return None

		# and convert it into something we can play with
		completed, response = self.dns_factory.normalizeResponse(response_s, extended=self.extended)

		# we might not have been sent all of the response yet
		if not completed:
			return None, None, None, True, None, None, None

		# check that we were able to properly parse the response
		if not response:
			return None

		# Try to get the IP address we asked for
		qtype, value = response.getValue()

		# If we didn't get the IP address then check to see if
		# we can find it by following the CNAMEs in the response
		if value is None:
			qtype, value = response.getChainedValue()


		chain_count = chained.get(response.identifier, 0)

		# watch out for loops
		if chain_count < 10:
			# Or the IPv4 address
			if value is None:
				related = response.getRelated()

				if response.qtype == 'A' and related is not None:
					newidentifier, newcomplete = self.resolveHost(related)
					newhost = related
					value = None

				elif response.qtype == 'A' and self.configuration.tcp6.out:
					qtype, value = response.getValue(qtype='AAAA')

					if value is None:
						newidentifier, newcomplete = self.resolveHost(response.qhost, qtype='AAAA')
						newhost = response.qhost

				elif response.qtype == 'AAAA':
					qtype, cname = response.getValue(qtype='CNAME')

					if cname is not None:
						newidentifier, newcomplete = self.resolveHost(cname)
						newhost = cname
					else:
						newidentifier, newcomplete = self.resolveHost(response.qhost, qtype='CNAME')
						newhost = response.qhost

			elif response.qtype == 'CNAME':
				newidentifier, newcomplete = self.resolveHost(value)
				newhost = value
				value = None

		return response.identifier, response.qhost, value, response.isComplete(), newidentifier, newhost, newcomplete

	def close (self):
		self.socket.close()



class UDPClient (DNSClient):
	extended = False

	def startConnecting (self):
		return socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)


class TCPClient (DNSClient):
	extended = True
	tcp_factory = staticmethod(connect)

	def __init__(self, w_id, dns_factory, configuration, servers):
		DNSClient.__init__(self, w_id, dns_factory, configuration, servers)
		self.reader = None
		self.writer = None

	def startConnecting (self):
		if self.configuration.tcp4.out:
			bind = self.configuration.tcp4.bind
		else:
			bind = self.configuration.tcp6.bind

		sock = self.tcp_factory(self.server, self.port, bind)
		return sock

	def _read (self, sock):
		data = ''

		while True:
			try:
				buffer_s = sock.recv(65535)
				if buffer_s:
					data += buffer_s

				yield data

			except socket.error, e:
				buffer_s = ''
				if e.errno in errno_block:
					yield ''
					continue

			else:
				if not buffer_s:
					break

		yield None

	def _write (self, sock, data):
		while data:
			try:
				while data:
					sent = sock.send(data)
					data = data[sent:]
					yield bool(data)

			except IOError, e:
				if e.errno in errno_block:
					yield None
				else:
					data = ''
					break
		yield False

	def readResponse (self):
		return self.reader.next()

	def continueSending (self):
		if self.writer:
			res = self.writer.next()
		else:
			res = None

		return res

	def resolveHost (self, hostname, qtype=None):
		"""Retrieve an A or AAAA entry for the requested hostname"""

		if qtype is None:
			if self.configuration.tcp4.out:
				qtype = 'A'
			else:
				qtype = 'AAAA'

		# create an A request ready to send on the wire
		identifier = self.next_identifier()
		request_s = self.dns_factory.createRequestString(identifier, qtype, hostname, extended=True)

		if request_s:
			# Explicitly close subroutines
			if self.writer:
				self.writer.close()

			if self.reader:
				self.reader.close()

			self.writer = self._write(self.socket, request_s)
			self.reader = self._read(self.socket)

			# and start sending it over the wire
			res = self.writer.next()
		else:
			res = False

		# let the manager know whether or not we have sent the entire query
		return identifier, res is False

	def close(self):
		self.socket.close()
		if self.reader:
			self.reader.close()

		if self.writer:
			self.writer.close()






class DNSResolver (object):
	DNSFactory = DNSPacketFactory
	UDPClientFactory = UDPClient
	TCPClientFactory = TCPClient

	def __init__ (self, configuration):
		self.next_identifier = next_identifier()
		self.configuration = configuration
		self.dns_factory = self.DNSFactory(configuration.dns.definitions)

		config = self.parseConfig(configuration.dns.resolver)
		self.servers = config['nameserver']

	def createUDPClient (self):
		return self.UDPClientFactory(0, self.dns_factory, self.configuration, self.servers)

	def createTCPClient (self):
		identifier = self.next_identifier()
		while identifier == 0:
			identifier = self.next_identifier()

		return self.TCPClientFactory(identifier, self.dns_factory, self.configuration, self.servers)

	def parseConfig(self, filename):
		"""Take our configuration from a resolv file"""

		try:
			result = {'nameserver': []}

			with open(filename) as fd:
				for line in (line.strip() for line in fd):
					if line.startswith('#'):
						continue

					option, value = (line.split(None, 1) + ['', ''])[:2]
					if option == 'nameserver':
						result['nameserver'].extend(value.split())
		except (TypeError, IOError):
			result = None

		return result
