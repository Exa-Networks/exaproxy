import random
import socket

from exaproxy.dns.resolver import DNSRequestFactory
from exaproxy.dns.resolver import DNSResponseFactory

from exaproxy.network.functions import connect

DEFAULT_RESOLV='/etc/resolv.conf'


class DNSClient(object):
	RequestFactory = DNSRequestFactory
	ResponseFactory = DNSResponseFactory

	def __init__(self, resolv=None, port=53):
		config = self.parseConfig(resolv or DEFAULT_RESOLV)
		self.servers = config['nameserver']
		self.port = port
		self._id = 0

	@property
	def server(self):
		return random.choice(self.servers)

	@property
	def nextid(self):
		res = self._id
		self._id += 1
		return res

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

	def isClosed(self):
		raise NotImplementedError



class UDPClient(DNSClient):
	def __init__(self, resolv, port):
		self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
		self.request_factory = self.RequestFactory()
		self.response_factory = self.ResponseFactory()

		# read configuration
		DNSClient.__init__(self, resolv, port)

	def resolveHost(self, hostname, qtype='A'):
		"""Retrieve an A or AAAA entry for the requested hostname"""

		# create an A request ready to send on the wire
		identifier = self.nextid
		request_s = self.request_factory.createRequestString(identifier, qtype, hostname)

		# and send it over the wire
		self.socket.sendto(request_s, (self.server, self.port))
		return identifier

	def getResponse(self):
		"""Read a response from the wire and return the desired result if present"""

		# Read the response from the wire
		response_s, peer = self.socket.recvfrom(65535)

		# and convert it into something we can play with
		response = self.response_factory.normalizeResponse(response_s)

		# Try to get the IP address we asked for
		value = response.getValue()

		# Or the IPv6 address
		if value is None:
			if response.qtype == 'A':
				value = response.getValue('AAAA')
			
		newidentifier = None
		if value is None:
			if response.qtype == 'A':
				newidentifier = self.resolveHost(hostname, qtype='AAAA')

		return response.identifier, response.qhost, value, response.isComplete(), newidentifier

	def isClosed(self):
		return False


class TCPClient(DNSClient):
	def __init__(self, resolv, port):
		# read configuration
		DNSClient.__init__(self, resolv, port)

		self.socket = self.startConnecting()
		self.request_factory = self.RequestFactory()
		self.reponse_factory = self.ResponseFactory()

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
			res = self.writer.send()
		else:
			res = None

		return res

	def resolveHost(self, hostname, qtype='A'):
		"""Retrieve an A or AAAA entry for the requested hostname"""

		# create an A request ready to send on the wire
		identifier = self.nextid
		request_s = self.request_factory.createRequestString(identifier, qtype, hostname)

		self.writer = self._write(self.socket, request_s)

		# and start sending it over the wire
		res = self.writer.next()

		# let the manager know whether or not we have sent the entire query
		return identifier if res else None

class DNSResolver(object):
	def createUDPClient(self,resolv,port=53):
		return UDPClient(resolv,port)

	def createTCPClient(self,resolv,port=53):
		return TCPClient(resolv,port)
