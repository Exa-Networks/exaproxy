from codec import DNSCodec
from codec import DNSRequestType
from codec import DNSResponseType

import struct

class DNSPacketFactory:
	request_factory = DNSRequestType
	response_factory = DNSResponseType

	def __init__(self, definitions):
		self.codec = DNSCodec(definitions)

	def serializeRequest(self, request, extended=False):
		encoded = self.codec.encodeRequest(request)
		if extended:
			encoded = struct.pack('>H', len(encoded)) + encoded

		return encoded

	def normalizeRequest(self, request_s, extended=False):
		if extended:
			(length,) = struct.unpack('>H', (request_s + '\0\0')[:2])
			request_s = request_s[2:]

			if length != len(request_s):
				request_s = ''

		return self.codec.decodeRequest(request_s)

	def createRequestString(self, identifier, request_type, request_name, extended=False):
		request = self.request_factory(identifier)
		request.addQuestion(request_type, request_name)

		encoded = self.codec.encodeRequest(request)
		if extended:
			encoded = struct.pack('>H', len(encoded)) + encoded

		return encoded

	def serializeResponse(self, response, extended=False):
		encoded = self.codec.encodeResponse(response)
		if extended:
			encoded = struct.pack('>H', len(encoded)) + encoded

		return encoded

	def normalizeResponse(self, response_s, extended=False):
		if extended:
			(length,) = struct.unpack('>H', (response_s + '\0\0')[:2])
			response_s = response_s[2:]

			if length != len(response_s):
				response_s = ''

		return self.codec.decodeResponse(response_s)
