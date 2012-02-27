#!/usr/bin/env python
# encoding: utf-8
"""
server.py

Created by Thomas Mangin on 2011-11-30.
Copyright (c) 2011 Exa Networks. All rights reserved.
"""

# http://code.google.com/speed/articles/web-metrics.html
# http://itamarst.org/writings/pycon05/fast.html

from exaproxy.util.logger import logger
from .functions import listen
import socket

class Server(object):
	_listen = staticmethod(listen)

	def __init__(self, poller, read_name):
		self.socks = {}
		self.poller = poller
		self.read_name = read_name

	def listen(self, ip, port, timeout, backlog):
		s = self._listen(ip, port,timeout,backlog)
		if s:
			self.socks[s] = True

			# register the socket with the poller
			self.poller.addReadSocket(self.read_name, s)

		return s

	def accept(self, sock):
		try:
			# should we check to make sure it's a socket we provided
			s, (ip,port) = sock.accept()
			s.setblocking(0)
			# NOTE: we really should try to handle the entire queue at once
			yield s, ip
		except socket.error, e:
			# It doesn't really matter if accept fails temporarily. We will
			# try again next loop
			logger.debug('server', 'failure on accept %s' % str(e))

	def stop(self):
		for sock in self.socks:
			try:
				sock.close()
			except socket.error:
				pass

		self.socks = {}
		self.poller.clearRead(self.read_name)
