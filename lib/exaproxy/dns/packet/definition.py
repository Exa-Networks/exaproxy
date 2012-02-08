#!/usr/bin/env python
# encoding: utf-8
"""
definition.py

Created by David Farrar on 2012-02-08.
Copyright (c) 2011 Exa Networks. All rights reserved.
"""

import inspect
import query
import response

# OPCODE:  Operation Type, 4 bits
#	   0: QUERY,  Standary query		RFC 1035
#	   1: IQUERY, Inverse query		RFC 1035, RFC 3425
#	   2: STATUS, Server status request	RFC 1035
#          3:
#          4: Notify				RFC 1996
#	   5: Update				RFC 2136
#	   6: RESERVED
#	  ... RESERVED
#	  15: RESERVED


#OPCODE, AA, TC, RD, RA, Z, AD, CD, RCODE


class DNSBaseType:
	QR = None
	OPCODE = 0   # Operation type

	def __init__(self, id):
		self.id = id


class DNSRequestType(DNSBaseType):
	QR = 0     # Query
	OPCODE = 0 # Query

	def __init__(self, id, queries=[]):
		self.id = id
		self.queries = []

		for q in queries:
			if not isinstance(q, query.DNSQueryType):
				raise ValueError, 'Invalid DNS Request'

			self.queries.append(q)

	def addQuery(self, querytype, name):
		q = dns_query_types.getTypeFromName(querytype, name)
		self.queries.append(q)

	def __str__(self):
		query_s = "\n\t ".join(str(q) for q in self.queries)

		return """DNS RESPONSE %(id)s
QUERIES: %(queries)s""" % {'id':self.id, 'queries':query_s}

class DNSResponseType(DNSBaseType):
	QR = 1      # Response
	OPCODE = 0

	def __init__(self, id, queries=[], responses=[], authorities=[], additionals=[]):
		self.id = id

		self.queries = queries
		self.responses = responses
		self.authorities = authorities
		self.additionals = additionals

	def __str__(self):
		query_s = "\n".join('\t' + str(q) for q in self.queries)
		response_s = "\n".join('\t' + str(r) for r in self.responses)
		authority_s = ''
		additional_s = ''

		return """DNS RESPONSE %(id)s
QUERIES: %(queries)s
RESPONSES: %(response)s
AUTHORITIES: %(authorities)s
ADDITIONAL: %(additional)s""" % {'id':self.id, 'queries':query_s, 'authorities':authority_s, 'additional':additional_s, 'response':response_s}



class DNSQueryTypes:
	# Easy access to Query classes

	def __init__(self):
		query_from_name = {}
		query_from_value = {}
		for name, item in inspect.getmembers(query):
			if inspect.isclass(item):
				if issubclass(item, query.DNSQueryType) and item is not query.DNSQueryType:
					query_from_name[item.NAME] = item
					query_from_value[item.VALUE] = item

		self.query_from_name = query_from_name
		self.query_from_value = query_from_value

	def decodeType(self, id, queryname):
		return self.query_from_value[id](queryname)

	def getTypeFromName(self, name, queryname):
		return self.query_from_name[name](queryname)


class DNSResponseTypes:
	def __init__(self):
		response_from_name = {}
		response_from_value = {}
		for name, item in inspect.getmembers(response):
			if inspect.isclass(item):
				if issubclass(item, response.DNSResponseType) and item is not response.DNSResponseType:
					response_from_name[item.NAME] = item
					response_from_value[item.VALUE] = item

		self.response_from_name = response_from_name
		self.response_from_value = response_from_value

	def decodeType(self, id, name, data):
		
		return self.response_from_value[id](name, data)

	def getTypeFromName(self, name, querytype, data):
		return self.response_from_name[name](queryname, data)

dns_query_types = DNSQueryTypes()
dns_response_types = DNSResponseTypes()


