#!/usr/bin/env python
# encoding: utf-8
"""
codec.py

Created by David Farrar on 2012-02-08.
Copyright (c) 2011 Exa Networks. All rights reserved.
"""

# DNS Header

#  Identification:   	Used to match reply packets to requests		16 bits
#  QR:			Query / Response				 1 bit
# XXX: complete


import struct
import convert

from definition import DNSRequestType, DNSResponseType
from definition import dns_query_types, dns_response_types


class DNSDecodedHeader:
	def __init__(self, packet_s):
		self.identifier = convert.u16(packet_s[0:2])  # 16 bits

		flags = convert.u16(packet_s[2:4])            # 16 bits
		self.qr = flags >> 15                         # 10000000 00000000
		self.opcode = (flags >> 11) & 15              # 01111000 00000000
		self.aa = (flags >> 10) & 1                   # 00000100 00000000
		self.tc = (flags >> 9) & 1                    # 00000010 00000000
		self.rd = (flags >> 8) & 1                    # 00000001 00000000
		self.ra = (flags >> 7) & 1                    # 00000000 10000000
		self.z =  (flags >> 6) & 1                    # 00000000 01000000
		self.ad = (flags >> 5) & 1                    # 00000000 00100000
		self.cd = (flags >> 4) & 1                    # 00000000 00010000
		self.rcode = flags & 1                        # 00000000 00001111

		self.query_len = convert.u16(packet_s[4:6])
		self.response_len = convert.u16(packet_s[6:8])
		self.authority_len = convert.u16(packet_s[8:10])
		self.additional_len = convert.u16(packet_s[10:12])

class DNSDecodedQuery:
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

class DNSDecodedResource :
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

	query_factory = dns_query_types.decodeType
	resource_factory = dns_response_types.decodeType

	def _decodeQueries(self, data, count, offset=12):
		queries = []
		names = {}

		for _ in xrange(count):
			query = DNSDecodedQuery(data)
			if query.queryname is None:
				return None, '', names, offset

			queries.append(query)
			bytes_read = len(query)
			data = data[bytes_read:]

			names[offset] = query.queryname
			offset += bytes_read

		return queries, data, names, offset

	def _decodeResources(self, data, packet_s, names, count, offset):
		resources = []

		for _ in xrange(count):
			resource = DNSDecodedResource(data, packet_s, names)
			if resource.queryname is None:
				return None, '', names, offset

			resources.append(resource)
			bytes_read = len(resource)
			data = data[bytes_read:]

			names[offset] = resource.queryname
			offset += bytes_read

		return resources, data, names, offset

	def _decodeHeader(self, message_s):
		if len(message_s) < 12:
			return None

		header = DNSDecodedHeader(message_s)
		data = message_s[12:]

		return header, data

	def decodeRequest(self, request_s):
		header, data = self._decodeHeader(request_s)
		if header.qr != 0:  # request
			return None

		queries, data, names, offset = self._decodeQueries(data, header.query_len)
		if queries is None:
			return None

		queries = [self.query_factory(q.querytype, q.queryname) for q in queries]
		return self.request_factory(header.identifier, queries)



	def decodeResponse(self, response_s):
		header, data = self._decodeHeader(response_s)
		if header.qr != 1:  # response
			return None

		queries, data, names, offset = self._decodeQueries(data, header.query_len)
		responses, data, names, offset = self._decodeResources(data, response_s, names, header.response_len, offset)
		authorities, data, names, offset = self._decodeResources(data, response_s, names, header.authority_len, offset)
		additionals, data, names, offset = self._decodeResources(data, response_s, names, header.additional_len, offset)

		queries = [self.query_factory(q.querytype, q.queryname) for q in queries]
		responses = [self.resource_factory(r.querytype, r.queryname, r.rdata, response_s) for r in responses]
		authorities = [self.resource_factory(r.querytype, r.queryname, r.rdata, response_s) for r in authorities]
		additionals = [self.resource_factory(r.querytype, r.queryname, r.rdata, response_s) for r in additionals]

		response = self.response_factory(header.identifier, queries, responses, authorities, additionals)
		return response

	def encodeRequest(self, request):
		header_s = struct.pack('>H2sH6s', request.identifier, '\1\0', len(request.queries), '\0\0\0\0\0\0')

		for q in request.queries:
			name = ''.join('%c%s' % (len(p), p) for p in q.name.split('.')) + '\0'
			header_s += struct.pack('>%ssHH' % len(name), name, q.VALUE, q.CLASS)

		return header_s


