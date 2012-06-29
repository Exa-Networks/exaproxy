# encoding: utf-8
"""
querytype.py

Created by David Farrar on 2012-02-08.
Copyright (c) 2011 Exa Networks. All rights reserved.
"""

import convert

class DNSType:
	def __str__(self):
		return str(self.question)

class DNSQueryType(DNSType):
	def __init__(self, querytype, question, dnsclass=1):
		self.dnsclass = dnsclass
		self.querytype = querytype
		self.question = question

	def __str__(self):
		return "Query of type %s for %s" % (self.querytype, self.question)

class DNSResourceType(DNSType):
	def __init__(self, querytype, question, response, ttl, dnsclass=1):
		self.dnsclass = dnsclass
		self.querytype = querytype
		self.question = question
		self.response = response
		self.ttl = ttl

	def __str__(self):
		return "Resource of type %s for %s: %s" % (self.querytype, self.question, self.response)


conversion = {
	'ipv4' : (convert.ipv4_to_dns, convert.dns_to_ipv4),
	'ipv6' : (convert.ipv6_to_dns, convert.dns_to_ipv6),
	'string' : (convert.string_to_dns, convert.dns_to_string),
	'unimplemented' : (None, None),
}



class DNSTypeFactory:
	CLASS = 1   # Internet

	def createQuery(self, name, question):
		return DNSQueryType(name, question)

	def createResource(name, question, response, ttl):
		return DNSResourceType(name, question, response, ttl)



class DNSTypeCodec:
	CLASS = 1   # Internet

	def __init__(self, definitions):
		self.byname = {}
		self.byvalue = {}

		self.parseConfiguration(definitions)

	def parseConfiguration(self, filename):
		try:
			with open(filename) as fd:
				for line in fd:
					line = line.strip().split('#', 1)[0]
					if line.startswith('#'):
						continue

					name, value, querytype = line.split()
					value = int(value)

					if name in self.byname:
						raise ValueError, 'Configuration file defines record of type %s more than once' % name

					if value in self.byvalue:
						raise ValueError, 'Configuration file defines record with value %s more than once' % value

					if querytype not in conversion:
						raise ValueError, 'Configuration file uses undefined type: %s' % querytype

					encoder, decoder = conversion[querytype]

					self.byname[name] = value, encoder
					self.byvalue[value] = name, decoder

		except (IndexError, ValueError):
			raise RuntimeError, 'Corrupt DNS type definition'
		except TypeError:
			raise RuntimeError, 'Corrupt DNS type definition'
		except IOError:
			raise RuntimeError, 'Cannot read DNS type definition file: %s' % filename

	def decodeQuery(self, value, question, data_s=''):
		name, decoder = self.byvalue.get(value, (None, None))
		return DNSQueryType(name, question)

	def encodeQuery(self, query, data_s=''):
		value, encoder = self.byname.get(query.querytype, (None, None))
		return value, query.question if value is not None else None

	def decodeResource(self, value, question, response, ttl, data_s=''):
		name, decoder = self.byvalue.get(value, (None, None))
		if name is not None and decoder is not None:
			decoded = decoder(response, data_s)
		else:
			decoded = None

		return DNSResourceType(name, question, decoded, ttl)

	def encodeResource(self, resource, data_s=''):
		value, encoder = self.byname.get(resource.querytype, (None, None))
		if value is not None:
			encoded = encoder(resource.response, data_s)
		else:
			encoded = None

		return value, resource.question, encoded, resource.ttl
