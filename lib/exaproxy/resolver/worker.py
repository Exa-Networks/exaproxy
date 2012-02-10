import random

from exaproxy.dns.resolver import DNSRequestFactory
from exaproxy.dns.resolver import DNSResponseFactory

DEFAULT_RESOLV='/etc/resolv.conf'


class DNSClient(object):
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





class UDPClient(DNSClient):
	RequestFactory = DNSRequestFactory
	ResponseFactory = DNSResponseFactory

	def __init__(self, resolv=None, port=53):
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
		response_s = self.socket.recvmsg(65535)

		# and convert it into something we can play with
		response = self.response_factory.decodeResponse(response_s)

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
