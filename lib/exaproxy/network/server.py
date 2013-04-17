# encoding: utf-8
"""
server.py

Created by Thomas Mangin on 2011-11-30.
Copyright (c) 2011-2013  Exa Networks. All rights reserved.
"""

# http://code.google.com/speed/articles/web-metrics.html
# http://itamarst.org/writings/pycon05/fast.html

from .functions import listen
import socket
import time

from exaproxy.util.log.logger import Logger
from exaproxy.configuration import load

configuration = load()
log = Logger('server', configuration.log.server)

class Server(object):
	_listen = staticmethod(listen)
	pause_warning_interval = 60

	def __init__(self, poller, read_name, max_clients):
		self.socks = {}
		self.poller = poller
		self.read_name = read_name
		self.max_clients = max_clients
		self.client_count = 0
		self.last_pause_warning = None

	def listen(self, ip, port, timeout, backlog):
		s = self._listen(ip, port,timeout,backlog)
		if s:
			self.socks[s] = True

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
			log.debug('failure on accept %s' % str(e))

		else:
			self.client_count += 1
		finally:
			if self.client_count >= self.max_clients:
				current_time = time.time()
				
				if self.last_pause_warning is None or (current_time - self.pause_warning_interval) > self.last_pause_warning:
					self.last_pause_warning = current_time
					log.warning('reached max configured number of clients (%s of %s). pausing' % (self.client_count, self.max_clients))
				for listening_sock in self.socks:
					self.poller.removeReadSocket(self.read_name, listening_sock)

	def notifyClose (self, client):
		paused = self.client_count >= self.max_clients
		self.client_count -= 1

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
