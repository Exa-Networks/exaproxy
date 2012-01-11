#!/usr/bin/env python
# encoding: utf-8
"""
server.py

Created by Thomas Mangin on 2011-11-30.
Copyright (c) 2011 Exa Networks. All rights reserved.
"""

# http://code.google.com/speed/articles/web-metrics.html

from nettools import bound_tcp_socket, socket
from .util.logger import logger


class Server(object):
	socket = staticmethod(bound_tcp_socket)

	def __init__(self):
		self.socks = {}
		self.name_generator = self._name_generator()

	def _name_generator(self):
		name = 0
		while True:
			yield str(name)
			name += 1

	def listen(self, ip, port, timeout, backlog):
		sock = self.socket(ip, port)
		if sock is not None:
			sock.settimeout(timeout)
			sock.listen(backlog)
			
			self.socks[sock] = True
		return sock

	def accept(self, sock):
		try:
			# should we check to make sure it's a socket we provided
			s, p = sock.accept()
			s.setblocking(0)
			# XXX: we really should try to handle the entire queue at once
			yield self.name_generator.next(), s, p
		except socket.error, e:
			# It doesn't really matter if accept fails temporarily. We will
			# try again next loop
			logger.debug('server', 'failure on accept %s' % str(e))

	def stop(self):
		for sock in self.socks:
			try:
				sock.close()
			except socket.error, e:
				pass

		self.socks = {}
