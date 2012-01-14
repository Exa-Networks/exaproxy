#!/usr/bin/env python
# encoding: utf-8
"""
server.py

Created by Thomas Mangin on 2011-11-30.
Copyright (c) 2011 Exa Networks. All rights reserved.
"""

# http://code.google.com/speed/articles/web-metrics.html
# http://itamarst.org/writings/pycon05/fast.html

import os
import struct
import time
import socket
import errno

from .util.logger import logger

class NetworkError (Exception):
	pass

class Server (object):
	_blocking_errs = set(
		errno.EAGAIN, errno.EWOULDBLOCK, 
		errno.EINTR, errno.ETIMEDOUT,
	)
	_soft_errs = set(
	)
	_fatal_errs = set(
		errno.ECONNABORTED, errno.EPIPE,
		errno.ECONNREFUSED, errno.EBADF,
		errno.ESHUTDOWN, errno.ENOTCONN,
		errno.ECONNRESET, 
	)

	def __init__ (self,ip,port,timeout,backlog,speed):
		self.io = None                  # The socket on which we are listening
		self.speed = speed              # How long do we wait in select when no data is available

		self.ip = ip                    # The ip we are listening on
		self.port = port                # The port we are listening on
		self.timeout = timeout          # The socket timeout (how long before we give up ..) -- XXX: 5 is too low
		self.backlog = backlog          # How many connection should the kernel buffer before refusing connections
	
		self.running = True             # Are we listening or have we finished
		self._loop = None        # Our co-routing loop

	def _ipv6 (self,addr):
		try:
			socket.inet_pton(socket.AF_INET6, addr)
		except socket.error:
			return False
		return True

	def connect (self):
		try:
			if self._ipv6(self.ip):
				self.io = socket.socket(socket.AF_INET6, socket.SOCK_STREAM, socket.IPPROTO_TCP)
				try:
					self.io.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
					self.io.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
				except AttributeError:
					pass
				self.io.settimeout(self.timeout)
				self.io.bind((self.ip,self.port,0,0))
			else:
				self.io = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
				try:
					self.io.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
					self.io.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
				except AttributeError:
					pass
				self.io.settimeout(self.timeout)
				self.io.bind((self.ip,self.port))
				self.io.setblocking(0)
				self.io.listen(self.backlog)
		except socket.error, e:
			if e.errno == errno.EADDRINUSE:
				logger.debug('server','could not listen, connection in use %s:%d' % (self.ip,self.port))
			if e.errno == errno.EADDRNOTAVAIL:
				logger.debug('server','could not listen, invalid address %s:%d' % (self.ip,self.port))
			logger.debug('server','could not listen on %s:%d - %s' % (self.ip,self.port,str(e)))
			self.close()

	def newClients (self):
		while True:
			try:
				sock,peer = self.io.accept()
				yield scoket,peer
			except socket.error, e:
				if e.errno in self._blocking_errs:
					break
				if e.errno in self._fatal_errs:
					raise NetworkError(str(e))
				raise NetworkError(str(e))
