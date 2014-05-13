#!/usr/bin/env python
# encoding: utf-8
from .request import ICAPRequestFactory
from .response import ICAPResponseFactory

def grouped (values):
	if not values:
		return

	end = len(values) - 1

	for pos in range(end):
		yield values[pos], values[pos+1]

	yield values[end], None

class ICAPParser (object):
	ICAPRequestFactory = ICAPRequestFactory
	ICAPResponseFactory = ICAPResponseFactory
	
	VERSIONS = ('ICAP/1.0',)
	METHODS = ('REQMOD', 'OPTIONS')
	HEADERS = ('cache-control', 'connection', 'date', 'trailer', 'upgrade', 'via',
			'authorization','allow','from','host','referer','user-agent', 'preview',
			'encapsulated','proxy-authenticate','proxy-authorization', 'istag')

	def __init__ (self, configuration):
		self.configuration = configuration
		self.request_factory = self.ICAPRequestFactory(configuration)
		self.response_factory = self.ICAPResponseFactory(configuration)

	def parseRequestLine (self, request_line):
		request_parts = request_line.split() if request_line else []

		if len(request_parts) == 3:
			method, url, version = request_parts
			method = method.upper()
			version = version.upper()

		else:
			method, url, version = None, None, None

		return method, url, version

	def parseResponseLine (self, response_line):
		response_parts = response_line.split() if response_line else []

		if len(response_parts) == 3:
			version, code, status = response_parts

			if code.isdigit():
				code = int(code)

			else:
				version, code, status = None, None, None

		else:
			version, code, status = None, None, None

		return version, code, status

	def readHeaders (self, request_lines):
		headers = {}

		for line in request_lines:
			if not line:
				break

			if ':' not in line:
				headers = None
				break

			key, value = line.split(':', 1)
			key = key.lower().strip()
			value = value.strip()

			if key in self.HEADERS or key.startswith('x-'):
				headers[key] = value

			if key == 'pragma' and ':' in value:
				pkey, pvalue = value.split(':', 1)
				pkey = pkey.lower().strip()
				pvalue = pvalue.strip()
				headers.setdefault(key, {})[pkey] = pvalue

		return headers

	def parseRequest (self, peer, icap_string, http_string):
		request_lines = (p for ss in icap_string.split('\r\n') for p in ss.split('\n'))
		try:
			request_line = request_lines.next()
		except StopIteration:
			request_line = None

		method, url, version = self.parseRequestLine(request_line)

		if method in self.METHODS and version in self.VERSIONS:
			headers = self.readHeaders(request_lines)
			site_name = url.rsplit(',',1)[-1] if ',' in url else 'default'
			headers['x-customer-name'] = site_name

		else:
			headers = None

		return self.request_factory.create(headers, icap_string, http_string) if headers else None

	def deencapsulate (self, encapsulated_line, body):
		if ':' in encapsulated_line:
			data = encapsulated_line.split(':', 1)[1]
			parts = (p.strip() for p in data.split(',') if '=' in p)
			pairs = (p.split('=',1) for p in parts)
			
			positions = dict((int(v),k) for (k,v) in pairs if v.isdigit())

		else:
			positions = {}

		for start, end in grouped(ordered(positions)):
			yield positions[start], body[start:end]
		

	def parseResponse (self, icap_string, http_string):
		response_lines = (p for ss in icap_string.split('\r\n') for p in ss.split('\n'))
		try:
			response_line = response_lines.next()
		except StopIteration:
			response_line = None

		version, code, status = self.parseResponseLine(response_line)

		if version in self.VERSIONS:
			headers = self.readHeaders(response_lines)
			headers['server'] = 'EXA Proxy 1.0'

		else:
			headers = {}

		encapsulated_line = headers.get('encapsulated', '')
		encapsulated = dict(self.deencapsulate(encapsulated_line, http_string))

		response_string = encapsulated.get('res-hdr', '')
		response_string += encapsulated.get('res-body', '')

		request_string = encapsulated.get('req-hdr', '')
		request_string += encapsulated.get('req-body', '')

		if request_string.startswith('CONNECT'):
			intercept_string, request_string = self.splitResponse(request_string)
			if not request_string:
				intercept_string, request_string = None, intercept_string

		else:
			intercept_string = None

		return self.response_factory.createRequestModification(version, code, status, headers, icap_string, request_string, response_string, intercept_string)

	def splitResponse (self, response_string):
		response_string = response_string.replace('\r\n', '\n')
		if '\n\n' in response_string:
			header_string, subheader_string = response_string.split('\n\n', 1)

		else:
			header_string, subheader_string = response_string, ''

		return header_string, subheader_string
