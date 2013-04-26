# encoding: utf-8
"""
request.py

Created by Thomas Mangin on 2012-02-27.
Copyright (c) 2011-2013 Exa Networks. All rights reserved.
"""

class Request (object):
	def __init__ (self,request):
		self.raw = request
		method, self.uri, version = request.split()
		self.method = method.upper()

		version = version.split('/')[-1]
		if version not in ('1.1', '1.0') and '.' in version:
			major, minor = version.split('.', 1)
			if major.isdigit() and minor.isdigit():
				version = str(int(major)) + '.' + str(int(minor))

		self.version = version

	def parse (self):
		# protocol
		if '://'  in self.uri:
			protocol, uri = self.uri.split('://', 1)
			# we have :// in the path
			if '/' in protocol:
				self.protocol = 'http'
				uri = self.uri
			else:
				self.protocol = protocol
		else:
			self.protocol = 'http'
			uri = self.uri

		# ipv6 host
		if uri.startswith('[') and ']' in uri:
			self.host, remaining = uri[1:].split(']', 1)
			if '/' in remaining:
				port,path = remaining.split('/')
				self.path = '/' + path
				if port:
					if not port.startswith(':'):
						raise ValueError('Malformed headers, ipv6 address was followed by an invalid port')

					self.port = self._checkport(port[1:])
				else:
					self.port = 80

				return self
			else:
				self.port = self._checkport(remaining)
				self.path = ''
				return self

		# split on path
		if '/' in uri:
			# we have a path
			host, path = uri.split('/', 1)
			self.path = '/' + path
			if ':' in host:
				self.host,port = host.split(':',1)
				self.port = self._checkport(port)
			else:
				self.host = host
				self.port = 80
		else:
			self.path = '/'
			if ':' in uri:
				self.host,port = uri.split(':',1)
				self.port = self._checkport(port)
			else:
				self.host = uri
				self.port = 80
		return self

	def _checkport (self,port):
		if port and not port.isdigit():
			raise ValueError('Malformed headers')
		return int(port)

	def __str__ (self):
		if self.protocol == 'http':
			return self.method + ' ' + self.path + ' HTTP/' + self.version

		return self.raw
