#!/usr/bin/env python
# encoding: utf-8
"""
http.py

Created by Thomas Mangin on 2011-12-02.
Copyright (c) 2011 Exa Networks. All rights reserved.
"""

import sys
import re
import socket
import errno

from .logger import Logger
logger = Logger()

from .version import version
from . import html

DEFAULT_READ_BUFFER_SIZE=4096

class regex:
	# XXX: Should this regex contain TRACE/CONNECT ?
	destination = re.compile("(GET|POST|PUT|HEAD|DELETE|OPTIONS|TRACE|CONNECT) (http://[^/]*|)(/[^ \r]*)(.*HTTP/.*\r?\nHost: ?)([^\r]*)(|\r?\n)", re.IGNORECASE)

	# Should we simply eat everything between : and \n to accept IPv6 address 
	x_forwarded_for = re.compile("(|\n)X-Forwarded-For: ?(((1?\d?\d)|(2([0-4]\d|5[0-5])))\.)(((1?\d?\d)|(2([0-4]\d|5[0-5])))\.)(((1?\d?\d)|(2([0-4]\d|5[0-5])))\.)((2([0-4]\d|5[0-5]))|(1?\d?\d))", re.IGNORECASE)

	connection = re.compile("\nConnection\s*:\s*([^\r\n]*)\s*\r?\n", re.IGNORECASE)

#450 Blocked by Windows Parental Controls
#A Microsoft extension. This error is given when Windows Parental Controls are turned on and are blocking access to the given webpage.
#598 Network read timeout error
#This status code is not specified in any RFCs, but is used by some[which?] HTTP proxies to signal a network read timeout behind the proxy to a client in front of the proxy.
#599 Network connect timeout error
#This status code is not specified in any RFCs, but is used by some[which?] HTTP proxies to signal a network connect timeout behind the proxy to a client in front of the proxy.


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

class HTTPParser (object):
	def parseRequest(self, request):
		r = regex.destination.match(request)
		if r is not None:
			# XXX: we want to have these returned to us rather than knowing
			# XXX: which group indexes we're interested in
			method = r.groups()[0].upper()
			path = r.groups()[2]
			host = r.groups()[4].lower()
		else:
			return None,None,None,None

		r = regex.x_forwarded_for.match(request)
		client = r.group(0) if r else '0.0.0.0'

		# David said ...
		# XXX: look at the regex I suggested to retrieve information from the request
		# XXX: there should be no need to do this here
		if not path.startswith('http://'):
			path = 'http://' + host + path

		return method, path, host, client


class HTTPFetcher (object):
	def __init__  (self,cid,host,port,request):
		self.io = None
		self._request = request
		self.cid = cid
		self.host = host
		self.port = port
		self._recv = self._fetch()

	def fileno (self):
		return self.io.fileno()

	def connect (self):
		logger.debug('connecting to webserver %s:%d' % (self.host,self.port), 'http %d' %self.cid)
		try:
			self.io = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
		except socket.error,e:
			logger.debug('problem create a connection to %s:%d' % (self.host,self.port), 'http %d' %self.cid)
			return False
		try:
			self.io.setblocking(0)
			self.io.connect((self.host, self.port))
			return True
		except socket.error,e:
			if e.errno in (errno.EINPROGRESS,):
				return True
			logger.debug('problem create a connection to %s:%d' % (self.host,self.port), 'http %d' %self.cid)
			self.close()
			return False

	def request (self):
		try:
			logger.debug('sending request to the website','http %d' % self.cid)
			number = self.io.send(self._request)
			logger.debug('sent %d bytes' % number,'http %d' % self.cid)
			self._request = self._request[number:]
			if not self._request:
				return True
			return False
		except socket.error,e:
#			if e.errno == errno.EISCONN:
#				break
#			if e.errno in (errno.EINPROGRESS,errno.EALREADY):
#				yield False
#				continue
			if e.errno in (errno.EAGAIN,errno.EWOULDBLOCK,errno.EINTR,errno.ENOTCONN):
				logger.debug('http client not ready yet for reading', 'http %d' %self.cid)
				return False
			# XXX: This may well be very incorrect
			logger.debug("problem sending request to %s:%d - %s" % (self.host,self.port,str(e)),'http %d' % self.cid)
			self.close()
			return None


	def fetch (self):
		return self._recv.next()

	def _fetch (self):
		logger.debug("waiting for data from %s:%d" % (self.host,self.port),'http %d' % self.cid)
		# Send the HTTP request to the remote website and yield True while working, otherwise yield None (and why not False ?)
		while True:
			try:
				content = self.io.recv(DEFAULT_READ_BUFFER_SIZE)
				if not content:
					# The socket is closed
					break
				yield content
			except socket.error,e:
				if e.errno in (errno.EAGAIN,errno.EWOULDBLOCK,errno.EINTR,):
					yield ''
					continue
				logger.debug('connection closed','http %d' % self.cid)
				break

		self.close()
		yield None

	def close (self):
		logger.debug('closing connection','http %d' % self.cid)
		try:
			self.io.shutdown(socket.SHUT_RDWR)
			self.io.close()
		except socket.error, e:
			pass
		self.runnning = False

class HTTPResponse (object):
	def __init__  (self,cid,code,title,body):
		self.cid = cid
		self.code = code
		self.title = title
		self.body = body
		self._recv = self._fetch()

	def fileno (self):
		return 0

	def request (self):
		return True

	def fetch (self):
		return self._recv.next()

	def _fetch (self):
		yield _http(self.code,html._html(self.title,self.body))
		yield None
