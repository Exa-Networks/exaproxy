# encoding: utf-8
"""
server.py

Created by Thomas Mangin on 2011-11-30.
Copyright (c) 2011-2013  Exa Networks. All rights reserved.
"""

# http://code.google.com/speed/articles/web-metrics.html
# http://itamarst.org/writings/pycon05/fast.html

from .functions import listen
from .functions import listen_intercept
import socket

from exaproxy.util.log.logger import Logger
from exaproxy.configuration import load

configuration = load()

class Server(object):
	_listen = staticmethod(listen)

	def __init__(self, name, poller, read_name, max_clients):
		self.socks = {}
		self.name = name
		self.poller = poller
		self.read_name = read_name
		self.max_clients = max_clients
		self.client_count = 0
		self.saturated = False  # we are receiving more connections than we can handle
		self.binding = set()
		self.serving = True  # We are currenrly listening
		self.log = Logger('server', configuration.log.server)
		self.log.info('server [%s] accepting up to %d clients' % (name, max_clients))


	def accepting (self):
		if self.serving:
			return True

		for ip, port, timeout, backlog in self.binding:
			try:
				self.log.critical('re-listening on %s:%d' % (ip,port))
				self.listen(ip,port,timeout,backlog)
			except socket.error,e:
				self.log.critical('could not re-listen on %s:%d : %s' % (ip,port,str(e)))
				return False
		self.serving = True
		return True

	def rejecting (self):
		if self.serving:
			for sock,(ip,port) in self.socks.items():
				self.log.critical('stop listening on %s:%d' % (ip,port))
				self.poller.removeReadSocket(self.read_name,sock)
				sock.close()
			self.socks = {}
			self.serving = False

	def saturation (self):
		if not self.saturated:
			return
		self.saturated = False
		self.log.error('we received more %s connections that we could handle' % self.name)
		self.log.error('we current have %s client(s) out of a maximum of %s' % (self.client_count, self.max_clients))

	def listen(self, ip, port, timeout, backlog):
		s = self._listen(ip, port,timeout,backlog)
		if s:
			self.binding.add((ip,port,timeout,backlog))
			self.socks[s] = (ip,port)

			# register the socket with the poller
			if self.client_count < self.max_clients:
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
			self.log.debug('%s could not accept a new connection %s' % (self.name,str(e)))
		else:
			self.client_count += 1
		finally:
			if self.client_count >= self.max_clients:
				self.saturated = True

				for listening_sock in self.socks:
					self.poller.removeReadSocket(self.read_name, listening_sock)

	def notifyClose (self, client, count=1):
		paused = self.client_count >= self.max_clients
		self.client_count -= count

		if paused and self.client_count < self.max_clients:
			for listening_sock in self.socks:
				self.poller.addReadSocket(self.read_name, listening_sock)

	def stop(self):
		for sock in self.socks:
			try:
				sock.close()
			except socket.error:
				pass

		self.socks = {}
		self.poller.clearRead(self.read_name)


class InterceptServer (Server):
	_listen = staticmethod(listen_intercept)
