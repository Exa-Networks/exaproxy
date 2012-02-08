import random

from .network.udp import UDPFactory
from .network.tcp import TCPFactory
from .factory.request import DNSRequestFactory

class DNSResolver:
	udp_socket_factory = UDPFactory()
	tcp_socket_factory = TCPFactory()
	request_factory = DNSRequestFactory()

	def __init__(self, resolv='/etc/resolv.conf'):
		config = self._parse(resolv)

		if not config:
			raise ConfigurationError, 'Could not read resolver configuration from %s' % resolv

		self.servers = config['nameserver']

	@property
	def nextid(self):
		res = self._nextid
		self._nextid += 1
		return res

	@property
	def server(self):
		return random.choice(self.servers)

	def _parse(self, filename):
		try:
			result = {'nameserver': []}

			with open(resolv) as fd:
				for line in (line.strip() for line in fd):
					if line.startswith('#'):
						continue

					option, value = (line.split(None, 1) + ('',))[:1]
					if option == 'nameserver':
						result['nameserver'].extend(value.split())
		except (TypeError, IOError):
			result = None

		return result

	def resolve(self, hostname):
		request = self.request_factory(self.nextid, hostname)
		data = self.dns_codec.serializeRequest(request)

		socket = self.udp_socket_factory.create(self.server, 53)
		socket.send(data)
		
		rdata = socket.recv(1024)
		response = self.dns_codec.normalizeResponse(rdata)

		if response.isTruncated():
			socket = self.tcp_socket_factory.create(self.server, 53)
			socket.send(data)

			rdata = self.tcp_socket_factory.read(socket)
			response = self.dns_codec.normalizeResponse(rdata)

		return response
