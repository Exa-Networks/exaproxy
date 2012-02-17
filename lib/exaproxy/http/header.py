#!/usr/bin/env python
# encoding: utf-8
"""
http.py

Created by Thomas Mangin on 2011-12-02.
Copyright (c) 2011 Exa Networks. All rights reserved.
"""

from exaproxy.util.logger import logger
from exaproxy.network.functions import isip

class HostMismatch(Exception):
	pass


class Header(dict):
	def __init__(self,configuration,header,remote_ip):
		self.order = []

		logger.info('header','parsing %s' % str(header))

		try:
			request, remaining = header.split('\r\n',1)

			method, pathstring, version = request.split()
			method = method.upper()
			version = version.split('/')[-1]
			
			protocol, pathstring = self.splitProtocol(pathstring)
			host, pathstring = self.splitHost(pathstring)
			port, path = self.splitPort(pathstring)

			if port and not port.isdigit():
				raise ValueError, 'Malformed headers'

			headers = self.parseHeader(remaining)
			self.update(headers)

			headerhost, _ = self.splitHost(headers.get('host', '').split(':', 1)[1].strip())

			if not host:
				host = headerhost

			if method == 'CONNECT':
				if 'host' not in self:
					self['host'] = 'Host: ' + host

			else:
				if host != headerhost:
					raise HostMismatch, 'Make up your mind: %s - %s' % (host, headerhost)


			# Is this the best place to add headers?
			self['x-proxy-version'] = "X-Proxy-Version: %s version %s" % (configuration.proxy.name, configuration.proxy.version)

			if configuration.http.x_forwarded_for:
				client = self.get('x-forwarded-for', ':%s' % remote_ip).split(':', 1)[1].split(',')[-1].strip()
				if not isip(client):
					logger.info('header', 'Invalid address in X-Forwarded-For: %s' % client)
					client = remote_ip
			else:
				client = remote_ip

			url = host + ((':'+port) if port is not None else '') + path
			port = int(port) if port else 80

			url_noport = host + path
		except KeyboardInterrupt:
			raise
		except Exception, e:
			logger.error('header','could not parse header %s %s' % (type(e),str(e)))
			method, path, version = None, None, None
			protocol, host, port, url = None, None, None, None
			url_noport = None
			client, request = None, None

		self.request = request
		self.method = method
		self.path = path
		self.version = version
		self.protocol = protocol
		self.host = host
		self.port = port
		self.url = url
		self.url_noport = url_noport
		self.client = client

	def __setitem__ (self,key,value):
		if key not in self.order:
			self.order.append(key)
		dict.__setitem__ (self,key,value)

	def update(self, other):
		for key, value in other.iteritems():
			if key not in self.order:
				self.order.append(key)

		dict.update(self, other)

	def pop(self, key, default=None):
		if key in self:
			res = dict.pop(self, key)
			self.order.remove(key)
		else:
			res = default

		return res

	def redirect(self, host, path):
		self.host = host if host is not None else self.host
		self.path = path if path is not None else self.path

		# XXX: need to handle port switch
		if path is not None:
			self.request = self.method + ' ' + path + 'HTTP/1.1'

		if host is not None:
			self['host'] = 'Host: ' + host

	def isValid(self):
		return self.method is not None and self.host is not None and self.path is not None

	def toString(self, linesep='\r\n'):
		request = str(self.method) + ' ' + str(self.path) + ' HTTP/1.1'
		return request + linesep + linesep.join(self[key] for key in self.order) + linesep + linesep


	def parseHeader(self, headerstring):
		headers = {}
		key = None
		data = ''

		for line in headerstring.split('\n'):
			line = line.strip('\r')
			if not line:
				break

			if line[0].isspace():
				if key:
					data += line.lstrip()
					continue
				else:
					raise ValueError, 'Whitespace before headers'

			if ':' not in line:
					raise ValueError, 'Malformed headers'

			if key: headers[key] = data

			key, value = line.split(':', 1)
			key = key.strip().lower()
			data = line
			if not key:
				raise ValueError, 'Malformed headers'

		if key is not None:
			headers[key] = data

		return headers

	def splitProtocol(self, pathstring):
		if '://' in pathstring:
			a, b = pathstring.split('://', 1)
			if '/' not in a:
				protocol = a
				pathstring = b
			else:
				protocol = 'http'
		else:
			protocol = 'http'

		return protocol, pathstring

	def splitHost(self, pathstring):
		if ':' in pathstring:
			# check to see if we have an IPv6 address
			if pathstring.startswith('[') and ']' in pathstring:
				host, remaining = pathstring[1:].split(']', 1)
			else:
				host, remaining = pathstring.split(':', 1)
				remaining = ':' + remaining

				if '/' in host:
					host, remaining = pathstring.split('/', 1)
					remaining = '/' + remaining
					
		elif '/' in pathstring:
			host, remaining = pathstring.split('/', 1)
			remaining = '/' + remaining

		else:
			host = pathstring
			remaining = '/'

		return host, remaining

	def splitPort(self, pathstring):
		if pathstring.startswith(':'):
			if '/' in pathstring:
				port, pathstring = pathstring[1:].split('/', 1)
				pathstring = '/' + pathstring
			else:
				port = None
				pathstring = pathstring[1:]
		else:
			port = None

		return port, pathstring
