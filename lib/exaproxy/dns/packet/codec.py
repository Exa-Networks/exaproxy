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
		self.id = convert.u16(packet_s[0:2])          # 16 bits

		flags = convert.u16(packet_s[2:4])          # 16 bits
		self.qr = flags >> 15                       # 10000000 00000000
		self.opcode = (flags >> 11) & 15            # 01111000 00000000
		self.aa = (flags >> 10) & 1                 # 00000100 00000000
		self.tc = (flags >> 9) & 1                  # 00000010 00000000
		self.rd = (flags >> 8) & 1                  # 00000001 00000000
		self.ra = (flags >> 7) & 1                  # 00000000 10000000
		self.z =  (flags >> 6) & 1                  # 00000000 01000000
		self.ad = (flags >> 5) & 1                  # 00000000 00100000
		self.cd = (flags >> 4) & 1                  # 00000000 00010000
		self.rcode = flags & 1                      # 00000000 00001111

		self.query_len = convert.u16(packet_s[4:6])
		self.response_len = convert.u16(packet_s[6:8])
		self.authority_len = convert.u16(packet_s[8:10])
		self.additional_len = convert.u16(packet_s[10:12])

class DNSDecodedQuery:
	def __init__(self, packet_s):
		data = packet_s
		total_read = 0
		parts = []
		while True:
			length = convert.u8(data[0])
			if length == 0:
				total_read += 1
				data = data[1:]
				break

			if len(data) < length:
				data = ''
				break

			total_read += length + 1
			parts.append(data[1:length+1])
			data = data[length+1:]

		ok = len(data) >= 4
		self.queryname = '.'.join(parts) if ok else None
		self.querytype = convert.u16(data[:2]) if ok else None
		self.queryclass = convert.u16(data[2:4]) if ok else None
		self._len = (total_read + 4) if ok else None

	def __len__(self):
		return self._len

class DNSDecodedResource :
	def __init__(self, data, names):
		total_read = 0
		parts = []

		offset = convert.u16(data[0:2])
		print 'want offset', offset & 0x3fff
		data = data[2:]
		if (offset >> 14) == 3:
			name = names.get(offset & 0x3fff)
		else:
			name = None

		if name:
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
		self._len = (total_read + 12 + rdata_len) if ok else None

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
				return None, '', None, None

			queries.append(query)
			bytes_read = len(query)
			data = data[bytes_read:]

			names[offset] = query.queryname
			offset += bytes_read

		return queries, data, names, offset

	def _decodeResources(self, data, names, count, offset):
		resources = []

		for _ in xrange(count):
			resource = DNSDecodedResource(data, names)
			if resource.queryname is None:
				return None, '', None, None

			resources.append(resource)
			bytes_read = len(resource)
			data = data[bytes_read:]

			names[offset] = resource.queryname
			print 'adding', offset
			print names
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
			print 1
			return None

		queries, data, names, offset = self._decodeQueries(data, header.query_len)
		if queries is None:
			return None

		queries = [self.query_factory(q.querytype, q.queryname) for q in queries]
		return self.request_factory(header.id, queries)



	def decodeResponse(self, response_s):
		header, data = self._decodeHeader(response_s)
		if header.qr != 1:  # response
			return None

		queries, data, names, offset = self._decodeQueries(data, header.query_len)
		responses, data, names, offset = self._decodeResources(data, names, header.response_len, offset)
		authorities, data, names, offset = self._decodeResources(data, names, header.authority_len, offset)
		additionals, data, names, offset = self._decodeResources(data, names, header.additional_len, offset)

		if None in (queries, responses, authorities, additionals):
			print queries, responses, authorities, additionals
			return None

		queries = [self.query_factory(q.querytype, q.queryname) for q in queries]
		responses = [self.resource_factory(r.querytype, r.queryname, r.rdata) for r in responses]
		authorities = [self.resource_factory(r.querytype, r.queryname, r.rdata) for r in authorities]
		additionals = [self.resource_factory(r.querytype, r.queryname, r.rdata) for r in additionals]

		response = self.response_factory(header.id, queries, responses, authorities, additionals)
		return response

	def encodeRequest(self, request):
		header_s = struct.pack('>H2sH6s', request.id, '\1\0', len(request.queries), '\0\0\0\0\0\0')

		for q in request.queries:
			name = ''.join('%c%s' % (len(p), p) for p in q.name.split('.')) + '\0'
			header_s += struct.pack('>%ssHH' % len(name), name, q.VALUE, q.CLASS)

		return header_s



if __name__ == '__main__':
	request = """\x6c\x1e\x81\x80\x00\x01\x00\x01\x00\x00\x00\x00\x03\x77\x77\x77\x0c\x65\x78\x61\x2d\x6e\x65\x74\x77\x6f\x72\x6b\x73\x02\x63\x6f\x02\x75\x6b\x00\x00\x01\x00\x01\xc0\x0c\x00\x01\x00\x01\x00\x00\x0d\xc2\x00\x04\x52\xdb\x03\x11"""

	codec = DNSCodec()

	request = DNSRequestType(1337)
	request.addQuery('A', 'www.decafbad.co.uk')

	request_s = codec.encodeRequest(request)
	#print codec.decodeRequest(request_s)

	import socket
	s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
	s.connect(('192.0.2.200', 53))
	s.send(request_s)
	response_s = s.recv(1024)

	response = codec.decodeResponse(response_s)
	print
	print response
