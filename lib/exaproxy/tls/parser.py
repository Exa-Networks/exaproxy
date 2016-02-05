# encoding: utf-8
from .request import TLSRequestFactory
from .response import TLSResponseFactory

from .decode import parse_hello

class TLSParser (object):
	TLSRequestFactory = TLSRequestFactory
	TLSResponseFactory = TLSResponseFactory

	def __init__ (self, configuration):
		self.configuration = configuration
		self.request_factory = self.TLSRequestFactory(configuration)
		self.response_factory = self.TLSResponseFactory(configuration)

	def parseClientHello (self, tls_header):
		hostname = parse_hello(tls_header)

		if not hostname:
			return None

		return self.request_factory.createClientHello(hostname)


	def encodeFailureResponse (self, response):
		return self.response_factory.createResponse(response.version, response.content_type, response.response, response.reason)
