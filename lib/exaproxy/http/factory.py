from .message import HTTP

class HTTPRequestFactory:
	def __init__ (self, configuration):
		self.configuration = configuration

	def parseRequest (self, peer, request_string):
		request = HTTP(self.configuration, request_string, peer)
		request.parse(True)
		return request
