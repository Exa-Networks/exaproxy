#!/usr/bin/env python
# encoding: utf-8
"""
http.py

Created by Thomas Mangin on 2011-12-02.
Copyright (c) 2011 Exa Networks. All rights reserved.
"""

class HostMismatch(Exception):
	pass

class Header(dict):
	def __init__(self, header):	
		self.order = []

		#print "********************************************* HEADER"
		#print header
		#print "********************************************* "

		try:
			request, remaining = header.split('\r\n',1)

			method, path, version = request.split()
			method = method.upper()
			version = version.upper()

			if '://' in path:
				path = path.split('://', 1)[1]

			if ':' in path:
				host_part, port_part = path.split(':', 1)
				if '/' not in host_part:
					host = host_part
					port = port_part
				else:
					host = path
					port = None

				if port:
					if '/' in port:
						port, path = port.split('/', 1)
						path = '/' + path
				else:
					if '/' in host:
						host, path = host.split('/', 1)
						path = '/' + path

			else:
				host = None
				port = None

			if method == 'CONNECT' and host:
				self.order.append('host')
				self['host'] = 'Host: ' + host is not None


			for line in remaining.split('\r\n'):
				key = line.split(':',1)[0].lower().strip()
				if not key:
					continue
				
				self.order.append(key)
				self[key] = line


			if method != 'CONNECT':
				requested_host = self.get('host', ':').split(':', 1)[1].strip()
				if host is not None and requested_host != host:
					raise HostMismatch, 'make up your mind: %s - %s' % (requested_host, host)

				host = requested_host

			client = self.get('x-forwarded-for', ':0.0.0.0').split(':')[1].split(',')[-1].strip()
			url = host + ((':'+port) if port is not None else '') + path
			port = port if port is not None else 80
		except KeyboardInterrupt:
			raise
		except Exception, e:
			print '+'*60
			print e
			print '+'*60
			method, path, version = None, None, None
			host, port, url = None, None, None
			client, request = None, None

		self.request = request
		self.method = method
		self.path = path
		self.version = version
		self.host = host
		self.port = port
		self.url = url
		self.client = client

	def isValid(self):
		return self.method is not None and self.host is not None and self.path is not None

	def toString(self, linesep='\r\n'):
		return self.request + linesep + linesep.join(self[key] for key in self.order) + linesep + linesep
