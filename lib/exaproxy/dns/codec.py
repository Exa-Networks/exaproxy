# encoding: utf-8
"""
codec.py

Created by David Farrar on 2012-02-08.
Copyright (c) 2011-2013  Exa Networks. All rights reserved.
"""

import struct
import convert

from definition import DNSRequestType, DNSResponseType
from dnstype import DNSTypeCodec

class DNSHeader:
	def __init__(self, packet_s):
		self.identifier = convert.u16(packet_s[0:2])                           # 16 bits

		flags = convert.u16(packet_s[2:4])                                     # 16 bits
		self.qr = flags >> 15              # query/response        (enum)      # 10000000 00000000
		self.opcode = (flags >> 11) & 15   # opcode                (enum)      # 01111000 00000000
		self.aa = (flags >> 10) & 1        # authoritative         (bool)      # 00000100 00000000
		self.tc = (flags >> 9) & 1         # truncated             (bool)      # 00000010 00000000
		self.rd = (flags >> 8) & 1         # recursion desired     (bool)      # 00000001 00000000
		self.ra = (flags >> 7) & 1         # recursion available   (bool)      # 00000000 10000000
		self.z  = (flags >> 6) & 1         # no idea - rfc2929 2.1             # 00000000 01000000
		self.ad = (flags >> 5) & 1         # authenticated         (bool)      # 00000000 00100000
		self.cd = (flags >> 4) & 1         # checking disabled     (bool)      # 00000000 00010000
		self.rcode = flags & 1             # return code                       # 00000000 00001111

		self.query_len = convert.u16(packet_s[4:6])                # no. of queries
		self.response_len = convert.u16(packet_s[6:8])             # no. of answer RRs
		self.authority_len = convert.u16(packet_s[8:10])           # no. of authority RRs
		self.additional_len = convert.u16(packet_s[10:12])         # no. of additional RRs


class DNSQuery:
	def __init__(self, data, packet_s, names):
		total_read, name = convert.dns_to_string_info(data, packet_s)

		if name:
			data = data[total_read:]
			ok = len(data) >= 4
		else:
			data = ''
			ok = False

		self.question = name if ok else None
		self.querytype = convert.u16(data[:2]) if ok else None
		self.queryclass = convert.u16(data[2:4]) if ok else None
		self._len = (total_read + 4) if ok else None

	def __len__(self):
		return self._len

class DNSResource:
	def __init__(self, data, packet_s, names):
		if data.startswith('\0'):
			name = '.'
			ptr = None
			total_read = 1
		else:
			total_read, name = convert.dns_to_string_info(data, packet_s)

		if name:
			data = data[total_read:]
			rdata_len = convert.u16(data[8:10])
			ok = len(data) >= 10 + rdata_len
		else:
			rdata_len = None
			ok = False

		self.question = name if ok else None
		self.querytype = convert.u16(data[:2]) if ok else None
		self.queryclass = convert.u16(data[2:4]) if ok else None
		self.ttl = convert.u32(data[4:8]) if ok else None
		self.rdata = data[10:10+rdata_len] if ok else None
		self._len = (total_read + 10 + rdata_len) if ok else None

	def __len__(self):
		return self._len







class DNSCodec:
	request_factory = DNSRequestType
	response_factory = DNSResponseType
	resourceFactory = DNSTypeCodec

	header_reader = DNSHeader
	query_reader = DNSQuery
	resource_reader = DNSResource

	def __init__(self, etc):
		self.resource_factory = self.resourceFactory(etc)

	def _decodeHeader(self, data):
		header = self.header_reader(data)
		data = data[12:]

		return header, data

	def _decodeRecords(self, data, count, decoder, packet_s, names, offset):
		records = []

		for _ in xrange(count):
			record = decoder(data, packet_s, names)

			# check for an error parsing the data
			if record.question is None:
				records = None
				data = ''
				break

			records.append(record)
			bytes_read = len(record)
			data = data[bytes_read:]

			names[offset] = record.question
			offset += bytes_read

		return records, data, names, offset

	def _decodeQueries(self, data, count, packet_s, names={}, offset=12):
		queries, data, names, offset = self._decodeRecords(data, count, self.query_reader, packet_s, names, offset)
		queries = [self.resource_factory.decodeQuery(q.querytype, q.question, packet_s) for q in queries] if queries is not None else None

		return queries, data, names, offset

	def _decodeResources(self, data, count, packet_s, names={}, offset=12):
		resources, data, names, offset = self._decodeRecords(data, count, self.resource_reader, packet_s, names, offset)
		resources = [self.resource_factory.decodeResource(r.querytype, r.question, r.rdata, r.ttl, packet_s) for r in resources] if resources is not None else None

		return resources, data, names, offset

	def createRequest(self, header, queries):
		identifier = header.identifier
		return self.request_factory(identifier, queries)

	def decodeRequest(self, request_s):
		header, data = self._decodeHeader(request_s)

		if header is None:
			request = None

		elif header.qr == 0:  # request
			queries, data, names, offset = self._decodeQueries(data, header.query_len, request_s)
			if queries:
				request = self.request_factory(header.identifier, queries)
			else:
				request = None
		else:
			request = None

		return request

	def encodeRequest(self, request):
		header_s = struct.pack('>HHH6s', request.identifier, request.flags, request.query_len, '\0\0\0\0\0\0')

		for q in request.queries:
			dnstype, question = self.resource_factory.encodeQuery(q)
			name = convert.string_to_dns(question)

			header_s += name + struct.pack('>HH', dnstype, q.dnsclass)

		return header_s

	def createResponse(self, header, queries=None, responses=None, authorities=None, additionals=None):
		identifier = header.identifier
		complete = bool(header.tc) is False
		return self.response_factory(identifier, complete, queries, responses, authorities, additionals)

	def decodeResponse(self, response_s):
		header, data = self._decodeHeader(response_s)

		if header.qr == 1:  # response
			queries, data, names, offset = self._decodeQueries(data, header.query_len, response_s)
			responses, data, names, offset = self._decodeResources(data, header.response_len, response_s, names, offset)
			authorities, data, names, offset = self._decodeResources(data, header.authority_len, response_s, names, offset)
			additionals, data, names, offset = self._decodeResources(data, header.additional_len, response_s, names, offset)

			response = self.createResponse(header, queries, responses, authorities, additionals)
		else:
			response = self.createResponse(header)

		return response

	def encodeResponse(self, response):
		header_s = struct.pack('>HHHHHH', response.identifier, 1<<15, response.query_len, response.response_len, response.authority_len, response.additional_len)

		for q in response.queries:
			dnstype, question = self.resource_factory.encodeQuery(q)
			name = convert.string_to_dns(question)

			header_s += name + struct.pack('>HH', dnstype, q.dnsclass)

		for r in response.resources:
			dnstype, question, decoded, ttl = self.resource_factory.encodeResource(r)
			name = convert.string_to_dns(question)

			new_header_s = name + struct.pack('>HHIH', dnstype, r.dnsclass, ttl, len(decoded)) + decoded
			header_s += new_header_s

		return header_s
