#!/usr/bin/env python
# encoding: utf-8
from .request import ICAPRequestFactory
from .response import ICAPResponseFactory
from .header import ICAPResponseHeaderFactory

class ICAPParser (object):
	ICAPResponseHeaderFactory = ICAPResponseHeaderFactory
	ICAPRequestFactory = ICAPRequestFactory
	ICAPResponseFactory = ICAPResponseFactory

	VERSIONS = ('ICAP/1.0',)
	METHODS = ('REQMOD', 'OPTIONS')
	HEADERS = ('cache-control', 'connection', 'date', 'trailer', 'upgrade', 'via',
			'authorization','allow','from','host','referer','user-agent', 'preview',
			'encapsulated','proxy-authenticate','proxy-authorization', 'istag')

	def __init__ (self, configuration):
		self.configuration = configuration
		self.header_factory = self.ICAPResponseHeaderFactory(configuration)
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
		response_parts = response_line.split(' ', 2) if response_line else []

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

	def parseRequest (self, icap_string, http_string):
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

		offsets = self.getOffsets(headers) if headers is not None else []
		length, complete = self.getBodyLength(offsets)

		if set(('res-hdr', 'res-body')).intersection(dict(offsets)):
			headers = None

		return self.request_factory.create(method, url, version, headers, icap_string, http_string, offsets, length, complete) if headers else None

	def getOffsets (self, headers):
		encapsulated_line = headers.get('encapsulated', '')

		parts = (p.strip() for p in encapsulated_line.split(',') if '=' in p)
		pairs = (p.split('=',1) for p in parts)
		offsets = ((k,int(v)) for (k,v) in pairs if v.isdigit())

		return sorted(offsets, lambda (_,a), (__,b): 1 if a >= b else -1)

	def getBodyLength (self, offsets):
		final, offset = offsets[-1] if offsets else ('null-body', 0)
		return offset, offset and final == 'null-body'

	def splitResponseParts (self, offsets, body_string):
		final, offset = offsets[-1] if offsets else (None, None)
		if final != 'null-body':
			offsets = offsets + [('null-body', len(body_string))]

		names = [name for name,offset in offsets]
		positions = [offset for name,offset in offsets]

		blocks = ((positions[i], positions[i+1]) for i in xrange(len(positions)-1))
		strings = (body_string[start:end] for start,end in blocks)

		return dict(zip(names, strings))

	def parseResponseHeader (self, header_string):
		response_lines = (p for ss in header_string.split('\r\n') for p in ss.split('\n'))
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

		offsets = self.getOffsets(headers) if headers is not None else []
		length, complete = self.getBodyLength(offsets)

		return self.header_factory.create(version, code, status, headers, header_string, offsets, length, complete)

	def continueResponse (self, response_header, body_string):
		version, code, status = response_header.info
		headers = response_header.headers
		header_string = response_header.header_string

		# split the body string into components
		parts = self.splitResponseParts(response_header.offsets, body_string)

		response_string = parts.get('res-hdr', '')
		request_string = parts.get('req-hdr', '')

		if request_string.startswith('CONNECT'):
			intercept_string, request_string = self.splitResponse(request_string)
			if not request_string:
				intercept_string, request_string = None, intercept_string

		else:
			intercept_string = None

		body_string = parts.get('res-body', '') if response_string else parts.get('req-body', '')

		return self.response_factory.create(version, code, status, headers, header_string, request_string, response_string, body_string, intercept_string)

	def splitResponse (self, response_string):
		for delimiter in ('\n\n', '\r\n\r\n'):
			if delimiter in response_string:
				header_string, subheader_string = response_string.split(delimiter, 1)
				break
		else:
			header_string, subheader_string = response_string, ''

		return header_string, subheader_string
