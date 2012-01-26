#!/usr/bin/env python
# encoding: utf-8
"""
poller.py

Created by Thomas Mangin on 2011-11-30.
Copyright (c) 2011 Exa Networks. All rights reserved.
"""

# http://code.google.com/speed/articles/web-metrics.html

from .network.poller import poll_select
from .util.logger import logger


class SocketPoller:
	poller = staticmethod(poll_select)

	def __init__(self, speed):
		self.speed = speed

		self.read_sockets = {}
		self.write_sockets = {}

		self.read_set = {}
		self.write_set = {}

		self.read_modified = {}
		self.write_modified = {}

		self.read_all = []
		self.write_all = []

	def addReadSocket(self, name, socket):
		# XXX: will raise if 'name' is not in self.read_sockets
		#      but this is much faster than checking it's there first
		sockets = self.read_sockets[name]
		if socket not in sockets:
			sockets.append(socket)
			self.read_set[name].add(socket)
			self.read_modified[name] = True

	def removeReadSocket(self, name, socket):
		sockets = self.read_sockets[name]
		if socket in sockets:
			sockets.remove(socket)
			self.read_set[name].remove(socket)
			self.read_modified[name] = True

	def setupRead(self, name):
		if name not in self.read_sockets:
			self.read_sockets[name] = []
			self.read_set[name] = set()

	def clearRead(self, name):
		had_sockets = bool(self.read_sockets[name])
		self.read_sockets[name] = {}

		if had_sockets:
			self.read_modified[name] = True
		
	def addWriteSocket(self, name, socket):
		# XXX: will raise if 'name' is not in self.write_sockets
		#      but this is much faster than checking it's there first
		sockets = self.write_sockets[name]
		if socket not in sockets:
			sockets.append(socket)
			self.write_set[name].add(socket)
			self.write_modified[name] = True

	def removeWriteSocket(self, name, socket):
		sockets = self.write_sockets[name]
		if socket in sockets:
			sockets.remove(socket)
			self.write_set[name].add(socket)
			self.write_modified[name] = True

	def setupWrite(self, name):
		if name not in self.write_sockets:
			self.write_sockets[name] = []
			self.write_set[name] = set()

	def clearWrite(self, name):
		had_sockets = bool(self.write_sockets[name])
		self.write_sockets[name] = {}

		if had_sockets:
			self.write_modified[name] = True

	def intersectingReadSockets(self, name, sockets):
		return self.read_set[name].intersection(sockets)

	def intersectingWriteSockets(self, name, sockets):
		return self.write_set[name].intersection(sockets)

	def poll(self):
		if self.read_modified:
			self.read_all = sum(self.read_sockets.values(), [])
			self.read_modified = {}

		if self.write_modified:
			self.write_all = sum(self.write_sockets.values(), [])
			self.write_modified = {}

		return self.poller(self.read_all, self.write_all, self.speed)

