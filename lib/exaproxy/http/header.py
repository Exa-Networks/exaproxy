#!/usr/bin/env python
# encoding: utf-8
"""
http.py

Created by Thomas Mangin on 2011-12-02.
Copyright (c) 2011 Exa Networks. All rights reserved.
"""

import traceback

from exaproxy.util.logger import logger
from exaproxy.network.functions import isip

#import re
#reg=re.compile('(\w+)[:=] ?"?(\w+)"?')
#reg=re.compile('(\w+)[:=] ?"?([^" ,]+)"?')
#dict(reg.findall(headers))


class HostMismatch(Exception):
	pass

class Request (object):
	def __init__ (self,request):
		method, self.uri, version = request.split()
		self.method = method.upper()
		self.version = version.split('/')[-1]

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
				self.port = self._checkport(port)
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
				self.port = '80'
		else:
			self.path = ''
			if ':' in uri:
				self.host,port = uri.split(':',1)
				self.port = self._checkport(port)
			else:
				self.host = uri
				self.port = '80'
		return self

	def _checkport (self,port):
		if port and not port.isdigit():
			raise ValueError, 'Malformed headers'
		return port

	def __str__ (self):
		return "%s %s HTTP/%s" % (self.method,self.path,self.version)

class Headers (object):
	def __init__ (self,separator):
		self._order = []
		self._data = {}
		self.separator = separator

	def get (self,key,default):
		return self._data.get(key,default)

	def set (self,key,value):
		if key in self._order:
			self._data[key].append(value)
			return self
		self._order.append(key)
		self._data[key] = [value]
		return self

	def replace (self,key,value):
		self._data[key] = [value]

	def default (self,key,value):
		if key not in self._data:
			self._data[key] = [value]

	def extend (self,key,value):
		self._data[key][-1] += value

	def pop (self, key, default=None):
		if key in self._data:
			value = self._data.pop(key)
			self._order.remove(key)
			return value
		else:
			return default

	def parse (self, lines):
		if lines[0].isspace():
			raise ValueError, 'Whitespace before headers'

#		try:
		if True:
			key = ''

			for line in lines.split(self.separator):
				if not line: break

				if line[0].isspace():
					# ValueError if key is not already there
					# IndexError the list is empty
					self.extend(key,line.lstrip())
					continue

				# KeyError if split does not return two elements
				key, value = line.split(':', 1)
				self.set(key.strip().lower(),line)
#		except (KeyError,TypeError,IndexError):
#			raise ValueError, 'Malformed headers'

		# we got a line starting with a :
		if '' in self._data:
			raise ValueError, 'Malformed headers'
		
		return self

	def __str__ (self):
		return self.separator.join([self.separator.join(self._data[key]) for key in self._order])


#class HTTP (object):
class Header (object):
	def __init__(self,configuration,headers,remote_ip):
		self.raw = headers
		self.ip = remote_ip
		self.proxy_name = "X-Proxy-Version: %s version %s" % (configuration.proxy.name, configuration.proxy.version)
		self.x_forwarded_for = configuration.http.x_forwarded_for

	def parse (self):
		logger.info('header','parsing %s' % str(self.raw))

		try:
			first, remaining = self.raw.split('\n',1)
			if '\r' in self.raw:
				self.separator = '\r\n'
				self.request = Request(first.rstrip('\r')).parse()
				self.headers = Headers('\r\n').parse(remaining)
			else:
				self.separator = '\n'
				self.request = Request(first).parse()
				self.headers = Headers('\n').parse(remaining)

			# Can you have a port here too ? I do not think so.
			self.headerhost = self.headers.get('host',[':'])[0].split(':',1)[1].strip()

			if self.request.host and self.request.host != '*':
				self.host = self.request.host
			else:
				# can raise KeyError, but host is a required header
				self.host = self.headerhost

			if self.host != self.headerhost and self.request.method != 'OPTIONS' and self.host != '*':
				raise HostMismatch, 'Make up your mind: %s - %s' % (self.host, self.headerhost)

			# David, why are you trying to force that header - broken clients ?
			# If we relay the version we should not have to add any headers.

			#if request.method == 'CONNECT':
			#	self.headers.default('host','Host: ' + request.host)

			# Is this the best place to add headers?
			self.headers.replace('x-proxy-version',self.proxy_name)

			if self.x_forwarded_for:
				client = self.headers.get('x-forwarded-for', ':%s' % self.ip).split(':', 1)[1].split(',')[-1].strip()
				if not isip(client):
					logger.info('header', 'Invalid address in X-Forwarded-For: %s' % client)
					client = self.ip
				self.client = client
			else:
				self.client = remote_ip

			self.content_length = int(self.headers.get('content-length', [':0'])[0].split(':',1)[1].strip())
			self.url = self.host + ((':%s' % self.request.port) if self.request.port is not None else '') + self.request.path
			self.url_noport = self.host + self.request.path

		except KeyboardInterrupt:
			raise
		except Exception, e:
			logger.error('header','could not parse header %s %s' % (type(e),str(e)))
			logger.error('header', traceback.format_exc())
			return None
		return self

	def redirect (self, host, path):
		self.host = host if host is not None else self.host
		self.path = path if path is not None else self.path

		# XXX: need to handle port switch
		if path is not None:
			self.request = self.method + ' ' + path + ' HTTP/' + self.version

		if host is not None:
			self.header.replace('host','Host: ' + host)

	def __str__ (self):
		return str(self.request) + self.separator + str(self.headers) + self.separator + self.separator


#if __name__ == '__main__':
#	class Conf (object):
#		class Proxy (object):
#			name = 'proxy'
#			version = '1'
#		proxy = Proxy()
#		class Http (object):
#			x_forwarded_for = True
#		http = Http()
#	conf = Conf()
#		
#	r = """\
#GET http://thomas.mangin.com/ HTTP/1.1
#Host: thomas.mangin.com
#User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10.7; rv:9.0.1) Gecko/20100101 Firefox/9.0.1
#Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8
#Accept-Language: en-us,en;q=0.5
#Accept-Encoding: gzip, deflate
#Accept-Charset: ISO-8859-1,utf-8;q=0.7,*;q=0.7
#Proxy-Connection: keep-alive
#Cookie: txtMainTab=Timeline
#
#"""
#	h = Header(conf,r,'127.0.0.1')
#	if h.parse():
#		print "[%s]" % h
#	else:
#		print 'parsing failed'