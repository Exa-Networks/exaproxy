#!/usr/bin/env python
# encoding: utf-8
"""
definition.py

Created by David Farrar on 2012-02-08.
Copyright (c) 2011 Exa Networks. All rights reserved.
"""

import random
import dnstype

# OPCODE:  Operation Type, 4 bits
#	   0: QUERY,  Standary query		RFC 1035
#	   1: IQUERY, Inverse query		RFC 1035, RFC 3425
#	   2: STATUS, Server status request	RFC 1035
#	  3:
#	  4: Notify				RFC 1996
#	   5: Update				RFC 2136
#	   6: RESERVED
#	  ... RESERVED
#	  15: RESERVED


#OPCODE, AA, TC, RD, RA, Z, AD, CD, RCODE


class DNSBaseType:
	QR = None
	OPCODE = 0   # Operation type

	def __init__(self, identifier):
		self.identifier = identifier


class DNSRequestType(DNSBaseType):
	QR = 0     # Query
	OPCODE = 0 # Query

	resource_factory = dnstype.DNSTypeFactory

	def __init__(self, identifier, queries=[]):
		self.identifier = identifier
		self.queries = queries

	def addQuestion(self, querytype, question):
		q = self.resource_factory.createQuestion(querytype, question)
		self.queries.append(q)

	def __str__(self):
		query_s = "\n\t ".join(str(q) for q in self.queries)

		return """DNS RESPONSE %(id)s
QUERIES: %(queries)s""" % {'id':self.identifier, 'queries':query_s}



class DNSResponseType(DNSBaseType):
	QR = 1      # Response
	OPCODE = 0

	def __init__(self, identifier, complete, queries=[], responses=[], authorities=[], additionals=[]):
		ok = complete is True and None not in (identifier, queries, responses, authorities, additionals)

		self.identifier = identifier if ok else None
		self.complete = bool(complete)
		self.queries = queries if ok else []
		self.responses = responses if ok else []
		self.authorities = authorities if ok else []
		self.additionals = additionals if ok else []


	def getResponse(self):
		info = {}

		for response in self.responses:
			info.setdefault(response.question, {}).setdefault(response.querytype, []).append(response.response)

		for response in self.authorities:
			info.setdefault(response.question, {}).setdefault(response.querytype, []).append(response.response)

		for response in self.additionals:
			info.setdefault(response.name, {}).setdefault(response.querytype, []).append(response.response)

		return info

	def extract(self, hostname, rdtype, info, seen=[]):
		data = info.get(hostname)

		if data:
			if rdtype in data:
				value = random.choice(data[rdtype])
			else:
				value = None
		else:
			value = None

		return value

	def getValue(self, question=None, qtype=None):
		if question is None or qtype is None:
			if self.queries:
				query = self.queries[0]

				if question is None:
					question = query.question

				if qtype is None:
					qtype = query.querytype

		info = self.getResponse()
		value =  self.extract(question, qtype, info)

	def isComplete(self):
		return self.complete

	def __str__(self):
		query_s = "\n".join('\t' + str(q) for q in self.queries)
		response_s = "\n\t".join('\t' + str(r) for r in self.responses)
		authority_s = "\n\t".join('\t' + str(r) for r in self.authorities)
		additional_s = "\n\t".join('\t' + str(r) for r in self.additionals)

		return """DNS RESPONSE %(id)s
QUERIES: %(queries)s
RESPONSES: %(response)s
AUTHORITIES: %(authorities)s
ADDITIONAL: %(additional)s""" % {'id':self.identifier, 'queries':query_s, 'authorities':authority_s, 'additional':additional_s, 'response':response_s}


