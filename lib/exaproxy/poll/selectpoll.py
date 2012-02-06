#!/usr/bin/env python
# encoding: utf-8
"""
poller.py

Created by Thomas Mangin on 2011-11-30.
Copyright (c) 2011 Exa Networks. All rights reserved.
"""

# http://code.google.com/speed/articles/web-metrics.html

from interface import IPoller

from exaproxy.network.poller import poll_select
from exaproxy.util.logger import logger


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
			all_socks[name], _, __ = self.poller(socks, [], 0)

		for name, socks in self.write_sockets.items():
			_, all_socks[name], __ = self.poller([], socks, 0)

		return all_socks

