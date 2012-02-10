from packet.codec import DNSCodec
from packet.codec import DNSRequestType

class DNSRequestFactory:
	request_factory = DNSRequestType
	codec = DNSCodec()

	def serializeRequest(self, request):
		return self.codec.encodeRequest(request)

	def normalizeRequest(self, request_s):
		return self.codec.decodeRequest(request_s)

	def createRequestString(self, identifier, request_type, request_name):
		request = self.request_factory(identifier)
		request.addQuery(request_type, request_name)

		return self.codec.encodeRequest(request)
