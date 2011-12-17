#!/usr/bin/env python
# encoding: utf-8
"""
http.py

Created by Thomas Mangin on 2011-12-02.
Copyright (c) 2011 Exa Networks. All rights reserved.
"""

import sys

from exaproxy.configuration import configuration

def _connect (code):
	return """\
HTTP/1.0 %d Connect Reply
Proxy-agent: exaproxy/%s (%s)

""" % (code,str(configuration.version),sys.platform)

# XXX: Replace the OK with a message related to the code :p

def _http (code,message):
	return """\
HTTP/1.1 %d OK
Date: Fri, 02 Dec 2011 09:29:44 GMT
Server: exaproxy/%s (%s)
Content-Length: %d
Connection: close
Content-Type: text/html
Cache-control: private
Pragma: no-cache

%s""" % (code,str(version),sys.platform,len(message),message)


class Header (dict):
	def __init__ (self,request):
		try:
			lines = request.split('\r\n')
			parts = lines.pop(0).split()

			for header in lines:
				if not header:
					break
				key,_ = header.split(':',1)
				self[key.lower()] = header

			self.method=parts[0].upper()
			self.path=parts[1]
			self.version=parts[2].upper()

			port = self.path.split(':',1)[-1].split('/')[0]
			if port.isdigit():
				self.port = int(port)
			else:
				self.port = 80

			if self.method == 'CONNECT':
				if not self.has_key('host'):
					self['host'] = 'Host:%s' % self.path.split(':',1)[0]
		except KeyboardInterrupt:
			raise
		except Exception:
			self.method = self.path = self.version = self.str = ''
			raise

	def __str__ (self):
		return ' '.join((self.method,self.path,self.version,'\r\n')) + '\r\n'.join(v for k,v in self.iteritems()) + '\r\n'

