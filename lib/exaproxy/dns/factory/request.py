from packet.codec import DNSCodec
from packet.codec import DNSRequestType

class DNSRequestFactory:
	request_factory = DNSRequestType
	codec = DNSCodec()

	def serializeRequest(self, request, extended=False):
		return self.codec.encodeRequest(request, extended)

	def normalizeRequest(self, request_s, extended=False):
		return self.codec.decodeRequest(request_s, extended)

	def createRequestString(self, identifier, request_type, request_name, extended=False):
		request = self.request_factory(identifier)
		request.addQuery(request_type, request_name)

		return self.codec.encodeRequest(request, extended)
