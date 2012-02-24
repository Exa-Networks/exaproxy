#!/usr/bin/env python
# encoding: utf-8
"""
poller.py

Created by Thomas Mangin on 2011-11-30.
Copyright (c) 2011 Exa Networks. All rights reserved.
"""

# http://code.google.com/speed/articles/web-metrics.html

import select
import socket

from exaproxy.util.logger import logger

from exaproxy.network.errno_list import errno_block
from interface import IPoller


def poll_select(read, write, timeout=None):
	try:
		r, w, x = select.select(read, write, read + write, timeout)
	except socket.error, e:
		if e.args[0] in errno_block:
			logger.error('select', 'select not ready, errno %d: %s' % (e.args[0], errno.errorcode.get(e.args[0], '')))
			return [], [], []

		if e.args[0] in errno_fatal:
			logger.error('select', 'select problem, errno %d: %s' % (e.args[0], errno.errorcode.get(e.args[0], '')))
			logger.error('select', 'poller read  : %s' % str(read))
			logger.error('select', 'poller write : %s' % str(write))
			logger.error('select', 'read : %s' % str(read))
		else:
			logger.error('select', 'select problem, debug it. errno %d: %s' % (e.args[0], errno.errorcode.get(e.args[0], '')))

		for f in read:
			try:
				poll([f], [], [f], 0.1)
			except socket.error:
				print "CANNOT POLL (read): %s" % str(f)
				logger.error('select', 'can not poll (read) : %s' % str(f))

		for f in write:
			try:
				poll([], [f], [f], 0.1)
			except socket.error:
				print "CANNOT POLL (write): %s" % str(f)
				logger.error('select', 'can not poll (write) : %s' % str(f))

		raise e
	except (ValueError, AttributeError, TypeError), e:
		logger.error('select',"fatal error encountered during select - %s %s" % (type(e),str(e)))
		raise e
	except select.error, e:
		if e.args[0] in errno_block:
			return [], [], []
		logger.error('select',"fatal error encountered during select - %s %s" % (type(e),str(e)))
		raise e
	except Exception, e:
		logger.error('select',"fatal error encountered during select - %s %s" % (type(e),str(e)))
		raise e

	return r, w, x


class SelectPoller (IPoller):
	poller = staticmethod(poll_select)

	def __init__(self, speed):
		self.speed = speed

		self.read_sockets = {}
		self.write_sockets = {}

		self.read_modified = {}
		self.write_modified = {}

		self.read_all = []
		self.write_all = []

	def addReadSocket(self, name, socket):
		sockets = self.read_sockets[name]
		if socket not in sockets:
			sockets.append(socket)
			self.read_modified[name] = True

	def removeReadSocket(self, name, socket):
		sockets = self.read_sockets[name]
		if socket in sockets:
			sockets.remove(socket)
			self.read_modified[name] = True

	def setupRead(self, name):
		if name not in self.read_sockets:
			self.read_sockets[name] = []

	def clearRead(self, name):
		had_sockets = bool(self.read_sockets[name])
		self.read_sockets[name] = {}

		if had_sockets:
			self.read_modified[name] = True

	def addWriteSocket(self, name, socket):
		sockets = self.write_sockets[name]
		if socket not in sockets:
			sockets.append(socket)
			self.write_modified[name] = True

	def removeWriteSocket(self, name, socket):
		sockets = self.write_sockets[name]
		if socket in sockets:
			sockets.remove(socket)
			self.write_modified[name] = True

	def setupWrite(self, name):
		if name not in self.write_sockets:
			self.write_sockets[name] = []

	def clearWrite(self, name):
		had_sockets = bool(self.write_sockets[name])
		self.write_sockets[name] = {}

		if had_sockets:
			self.write_modified[name] = True

	corkReadSocket = removeReadSocket
	uncorkReadSocket = addReadSocket

	corkWriteSocket = removeWriteSocket
	uncorkWriteSocket = addWriteSocket

	def poll(self):
		all_socks = {}

		for name, socks in self.read_sockets.items():
			socks, _, __ = self.poller(socks, [], 0)
			if socks:
				all_socks[name] = socks

		for name, socks in self.write_sockets.items():
			_, socks, __ = self.poller([], socks, 0)
			if socks:
				all_socks[name] = socks

		if all_socks:
			return all_socks

		if self.read_modified:
			self.read_all = sum(self.read_sockets.values(), [])
			self.read_modified = {}

		if self.write_modified:
			self.write_all = sum(self.write_sockets.values(), [])
			self.write_modified = {}

		r, w, x  = self.poller(self.read_all, self.write_all, self.speed)

		for name, socks in self.read_sockets.items():
			polled, _, __ = self.poller(socks, [], 0)
			if polled: all_socks[name] = polled

		for name, socks in self.write_sockets.items():
			polled, all_socks[name], __ = self.poller([], socks, 0)
			if polled: all_socks[name] = polled

		return all_socks

