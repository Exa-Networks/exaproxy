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


class DNSClient(object):
	DNSFactory = DNSPacketFactory
	tcp_factory = staticmethod(connect)

	def __init__(self, configuration, resolv=None, port=53):
		self.configuration = configuration
		self.dns_factory = self.DNSFactory(configuration.dns.definitions)
		config = self.parseConfig(resolv)
		self.servers = config['nameserver']
		self.port = port
		self.extended = False
		self.next_identifier = next_identifier()

	@property
	def server(self):
		return random.choice(self.servers)

	def parseConfig(self, filename):
		"""Take our configuration from a resolv file"""

		try:
			result = {'nameserver': []}

			with open(filename) as fd:
				for line in (line.strip() for line in fd):
					if line.startswith('#'):
						continue

					option, value = (line.split(None, 1) + [''])[:2]
					if option == 'nameserver':
						result['nameserver'].extend(value.split())
		except (TypeError, IOError):
			result = None

		return result

	def resolveHost(self, hostname, qtype=None):
		"""Retrieve an A or AAAA entry for the requested hostname"""

		if qtype is None:
			if self.configuration.tcp4.out:
				qtype = 'A'
			else:
				qtype = 'AAAA'

		# create an A request ready to send on the wire
		identifier = self.next_identifier()
		request_s = self.dns_factory.createRequestString(identifier, qtype, hostname)

		# and send it over the wire
		try:
			self.socket.sendto(request_s, (self.server, self.port))
		except IOError, e:
			pass
		return identifier, True

	def getResponse(self):
		"""Read a response from the wire and return the desired result if present"""

		# We may need to make another query
		newidentifier = None
		newcomplete = True
		newhost = None

		# Read the response from the wire
		response_s, peer = self.socket.recvfrom(65535)

		# and convert it into something we can play with
		response = self.dns_factory.normalizeResponse(response_s, extended=self.extended)

		# Try to get the IP address we asked for
		value = response.getValue()

		# Or the IPv4 address
		if value is None:
			if response.qtype == 'A' and self.configuration.tcp6.out:
				value = response.getValue('AAAA')

				if value is None:
					newidentifier, newcomplete = self.resolveHost(response.qhost, qtype='AAAA')
					newhost = response.qhost

			elif response.qtype == 'AAAA':
				cname = response.getValue('CNAME')

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

	def shouldClose(self):
		raise NotImplementedError

	def close (self):
		pass



class UDPClient(DNSClient):
	def __init__(self, configuration, resolv, port):
		self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)

		# read configuration
		DNSClient.__init__(self, configuration, resolv, port)


	def shouldClose(self):
		return False


class TCPClient(DNSClient):
	def __init__(self, configuration, resolv, port):
		# read configuration
		DNSClient.__init__(self, configuration, resolv, port)
		self.extended = True

		self.socket = self.startConnecting()
		self.dns_factory = self.DNSFactory(configuration.dns.definitions)
		self.next_identifier = next_identifier()

		self.reader = None
		self.writer = None

	def startConnecting(self):
		sock = self.tcp_factory(self.server, self.port)
		return sock

	def _read(self, sock):
		data = ''
		while True:
			buffer = sock.recv(65535)
			if buffer:
				data += buffer
				yield None

		yield data

	def _write(self, sock, data):
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

	def continueSending(self):
		if self.writer:
			res = self.writer.next()
		else:
			res = None

		return res

	def resolveHost(self, hostname, qtype=None):
		"""Retrieve an A or AAAA entry for the requested hostname"""

		if qtype is None:
			if self.configuration.tcp4.out:
				qtype = 'A'
			else:
				qtype = 'AAAA'

		# create an A request ready to send on the wire
		identifier = self.next_identifier()
		request_s = self.dns_factory.createRequestString(identifier, qtype, hostname, extended=True)

		self.writer = self._write(self.socket, request_s)

		# and start sending it over the wire
		res = self.writer.next()

		# let the manager know whether or not we have sent the entire query
		return identifier, res is False

	def shouldClose(self):
		return True

	def close(self):
		self.socket.close()

class DNSResolver(object):
	def createUDPClient(self,configuration,resolv,port=53):
		return UDPClient(configuration,resolv,port)

	def createTCPClient(self,configuration,resolv,port=53):
		return TCPClient(configuration,resolv,port)
