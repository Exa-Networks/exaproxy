from codec import DNSCodec
from codec import DNSRequestType
from codec import DNSResponseType

class DNSPacketFactory:
	request_factory = DNSRequestType
	response_factory = DNSResponseType

	def __init__(self, configuration):
		base = configuration.get('etc-dns')
		self.codec = DNSCodec(base)

	def serializeRequest(self, request, extended=False):
		encoded = self.codec.encodeRequest(request)
		if extended:
			encoded = struct.pack('>Hs', len(encoded), encoded)

		return encoded

	def normalizeRequest(self, request_s, extended=False):
		if extended:
			length, request_s = struct.unpack('>Hs', request_s)
			if length != len(request_s):
				request_s = ''

		return self.codec.decodeRequest(request_s, extended)

	def createRequestString(self, identifier, request_type, request_name, extended=False):
		request = self.request_factory(identifier)
		request.addQuery(request_type, request_name)

		encoded = self.codec.encodeRequest(request, extended)
		if extended:
			encoded = struct.pack('>Hs', len(encoded), encoded)

		return encoded

	def serializeResponse(self, response, extended=False):
		encoded = self.codec.encodeResponse(response)
		if extended:
			encoded = struct.pack('>Hs', len(encoded), encoded)

		return encoded

	def normalizeResponse(self, response_s, extended=False):
		if extended:
			length, request_s = struct.unpack('>Hs', response_s)
			if length != len(response_s):
				request_s = ''

		return self.codec.decodeResponse(response_s)
