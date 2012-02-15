from packet.codec import DNSCodec
from packet.codec import DNSResponseType

class DNSResponseFactory:
	request_factory = DNSResponseType
	codec = DNSCodec()

	def createResponse(self, identifier):
		response = self.response_factory(identifier)
		return response

	def serializeResponse(self, response):
		return self.codec.encodeResponse(reponse)

	def normalizeResponse(self, response, extended=False):
		return self.codec.decodeResponse(response, extended)
