#!/usr/bin/env python
# encoding: utf-8
from .request import ICAPRequestFactory

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
			headers = None

		return self.response_factory.create(version, code, status, headers, icap_string, http_string)
