#!/usr/bin/env python
# encoding: utf-8
"""
codec.py

Created by David Farrar on 2012-02-08.
Copyright (c) 2011 Exa Networks. All rights reserved.
"""

import struct
import convert

from definition import DNSRequestType, DNSResponseType


class DNSHeaderDecoder:
	def __init__(self, packet_s):
		self.identifier = convert.u16(packet_s[0:2])                           # 16 bits

		flags = convert.u16(packet_s[2:4])                                     # 16 bits
		self.qr = flags >> 15              # query/response        (enum)      # 10000000 00000000
		self.opcode = (flags >> 11) & 15   # opcode                (enum)      # 01111000 00000000
		self.aa = (flags >> 10) & 1        # authoritative         (bool)      # 00000100 00000000
		self.tc = (flags >> 9) & 1         # truncated             (bool)      # 00000010 00000000
		self.rd = (flags >> 8) & 1         # recursion desired     (bool)      # 00000001 00000000
		self.ra = (flags >> 7) & 1         # recursion available   (bool)      # 00000000 10000000
		self.z =  (flags >> 6) & 1         # no idea - rfc2929 2.1             # 00000000 01000000
		self.ad = (flags >> 5) & 1         # authenticated         (bool)      # 00000000 00100000
		self.cd = (flags >> 4) & 1         # checking disabled     (bool)      # 00000000 00010000
		self.rcode = flags & 1             # return code                       # 00000000 00001111

		self.query_len = convert.u16(packet_s[4:6])                # no. of queries   
		self.response_len = convert.u16(packet_s[6:8])             # no. of answer RRs
		self.authority_len = convert.u16(packet_s[8:10])           # no. of authority RRs
		self.additional_len = convert.u16(packet_s[10:12])         # no. of additional RRs

class DNSQueryDecoder:
	def __init__(self, data):
		queryname, ptr = convert.dns_string(data)
		if queryname:
			total_read = len(queryname)+2
			data = data[total_read:]
		else:
			total_read = None
			data = ''

		ok = len(data) >= 4
		self.queryname = queryname if ok else None
		self.querytype = convert.u16(data[:2]) if ok else None
		self.queryclass = convert.u16(data[2:4]) if ok else None
		self._len = (total_read + 4) if ok else None

	def __len__(self):
		return self._len

class DNSResourceDecoder :
	def __init__(self, data, packet_s, names):
		name, ptr = convert.dns_string(data)
		total_read = len(name) + 2

		if ptr is not None:
			parts = [name] if name else []
			extra = convert.dns_to_string(packet_s[ptr:], packet_s)

			if extra is not None:
				parts += [extra] if extra else []
				name = '.'.join(parts)
			else:
				name = None

		if name:
			data = data[total_read:]
			rdata_len = convert.u16(data[8:10])
			ok = len(data) >= 10 + rdata_len
		else:
			rdata_len = None
			ok = False

		self.queryname = name if ok else None
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

	header_decoder = DNSHeaderDecoder
	query_decoder = DNSQueryDecoder
	resource_decoder = DNSResourceDecoder

	def _decodeHeader(self, data):
		if len(data) >= 12:
			header = self.header_decoder(data)
			data = data[12:]
		else:
			header = None
			data = ''

		return header, data

	def _decodeRecords(self, data, count, decoder, packet_s, names={}, offset=12):
		records = []

		for _ in xrange(count):
			record = decoder(data, packet_s, names)

			# check for an error parsing the data
			if record.queryname is None:
				records = None
				data = ''
				break

			records.append(record)
			bytes_read = len(record)
			data = data[bytes_read:]

			names[offset] = record.queryname
			offset += bytes_read

		return records, data, names, offset

	def _decodeQueries(self, data, count, packet_s, names={}, offset=12):
		return self._decodeRecords(data, count, self.query_decoder, packet_s, names, offset)

	def _encodeQueries(self, data, count, names={}, offset=12):
		return self._encodeRecords(data, count, self.query_encoder, names, offset)

	def _decodeResources(self, data, count, packet_s, names={}, offset=12):
		return self._decodeRecords(data, count, self.resource_decoder, packet_s, names, offset)

	def _encodeResources(self, data, count, names={}, offset=12):
		return self._encodeRecords(data, count, self.response_encoder, names, offset)


	def createRequest(self, header, queries=[]):
		identifier = header.identifier
		queries = [self.createQuery(q.querytype, q.queryname) for q in queries]

		return self.request_factory(identifier, queries)
		
	def decodeRequest(self, request_s):
		header, data = self._decodeHeader(request_s)

		if header.qr == 0:  # request
			queries, data, names, offset = self._decodeQueries(data, header.query_len, request_s)
			request = self.request_factory(header, queries)
		else:
			request = self.request_factory(header)

		return request

	def encodeRequest(self, request):
		header_s = struct.pack('>HHH6s', request.identifier, request.flags, request.query_len, '\0\0\0\0\0\0')

		for q in request.queries:
			name = convert.string_to_dns(q.name)
			header_s += struct.pack('>sHH', name, q.TYPE, q.CLASS)

		return header_s



	def createResponse(self, header, queries, responses, authorities, additionals):

	def decodeResponse(self, response_s):
		header, data = self._decodeHeader(response_s)

		if header.qr == 1: # response
			queries, data, names, offset = self._decodeQueries(data, header.query_len, response_s)
			responses, data, names, offset = self._decodeResources(data, header.response_len, response_s, names, offset)
			authorities, data, names, offset = self._decodeResources(data, header.authority_len, response_s, names, offset)
			additionals, data, names, offset = self._decodeResources(data, header.additional_len, response_s, names, offset)

			response = self.response_factory(header, queries, responses, authorities, additionals)
		else:
			response = self.response_factory(header)

		return response

	def encodeResponse(self, response):
		header_s = struct.pack('>HHHHHH', response.identifier, response.flags, response.query_len, response.response_len, response.authority_len, response.additional_len)

		for q in response.queries:
			name = convert.string_to_dns(q.name)
			header_s += struct.pack('>sHH', name, q.TYPE, q.CLASS)

		for r in response.resources:
			name = convert.string_to_dns(r.name)
			value = r.dns_data
			header_s += struct.pack('>sHHIHs', name, r.TYPE, r.CLASS, r.ttl, len(value), value)

		return header_s
