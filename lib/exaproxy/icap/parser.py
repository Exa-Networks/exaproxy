#!/usr/bin/env python
# encoding: utf-8
from .request import ICAPRequestFactory
from exaproxy.http.factory import HTTPRequestFactory

class ICAPParser (object):
	ICAPFactory = ICAPRequestFactory
	HTTPFactory = HTTPRequestFactory
	
	VERSIONS = ('ICAP/1.0',)
	METHODS = ('REQMOD', 'OPTIONS')
	HEADERS = ('cache-control', 'connection', 'date', 'pragma', 'trailer', 'upgrade', 'via',
			'authorization','allow','from','host','referer','user-agent', 'preview',
			'encapsulated','proxy-authenticate','proxy-authorization')

	def __init__ (self, configuration):
		self.configuration = configuration
		self.http_factory = self.HTTPFactory(configuration)
		self.icap_factory = self.ICAPFactory(configuration)

	def parseRequestLine (self, request_line):
		request_parts = request_line.split() if request_line else []

		if len(request_parts) == 3:
			method, url, version = request_parts
		else:
			method, url, version = None, None, None

		return method, url, version

	def readHeaders (self, request_lines):
		headers = {}

		for line in request_lines:
			if not line:
				break

			if ':' not in line:
				headers = None
				break

			key, value = line.split(':', 1)
			key = key.lower()

			if key in self.HEADERS or key.startswith('x-'):
				headers[key] = value

		return headers

	def parseRequest (self, peer, icap_string, http_string):
		request_lines = (p for ss in icap_string.split('\r\n') for p in ss.split('\n'))
		try:
			request_line = request_lines.next()
		except StopIteration:
			request_line = None

		method, url, version = self.parseRequestLine(request_line)
		method = method.upper() if method is not None else None
		version = version.upper() if version is not None else None

		if method in self.METHODS and version in self.VERSIONS:
			headers = self.readHeaders(request_lines)
		else:
			headers = None

		site_name = url.rsplit(',',1)[-1] if ',' in url else 'default'
		headers['x-customer-name'] = site_name

		http_request = self.http_factory.parseRequest(peer, http_string) if headers else None
		icap_request = self.icap_factory.create(headers, http_request, icap_string, http_string) if http_request else None

		return icap_request
