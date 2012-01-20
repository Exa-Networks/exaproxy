#!/usr/bin/env python
# encoding: utf-8
"""
server.py

Created by David Farrar  on 2011-11-30.
Copyright (c) 2011 Exa Networks. All rights reserved.
"""

# XXX: David, please add logging here ..

from exaproxy.util.logger import logger
from browser import Client

class ClientManager (object):
	def __init__(self):
		self.norequest = {}
		self.bysock = {}
		self.byname = {}
		self.buffered = []
		self._nextid = 0

	def __contains__(self, item):
		return item in self.byname

	def getnextid(self):
		self._nextid += 1
		return str(self._nextid)

	def newConnection(self, sock, peer):
		name = self.getnextid()
		client = Client(name, sock, peer)

		self.norequest[sock] = client
		self.byname[name] = client

		logger.info('client','new id %s (socket %s) in clients : %s' % (name, sock, sock in self.bysock))
		return peer

	def readRequest(self, sock):
		"""Read only the initial HTTP headers sent by the client"""

		client = self.norequest.get(sock, None)
		if client:
			name, peer, request, content = client.readData()
			if request:
				# headers can be read only once
				self.norequest.pop(sock, None)

			elif request is None:
				self.cleanup(sock, client.name)
		else:
			logger.error('client','trying to read headers from a client that does not exist %s' % sock)
			name, peer, request, content = None, None, None, None

		return name, peer, request, content


	def readDataBySocket(self, sock):
		client = self.bysock.get(sock, None)
		if client:
			name, peer, request, content = client.readData()
			if request is None:
				self.cleanup(sock, client.name)
		else:
			logger.error('client','trying to read from a client that does not exist %s' % sock)
			name, peer, request, content = None, None, None, None


		return name, peer, request, content


	def readDataByName(self, name):
		client = self.byname.get(name, None)
		if client:
			name, peer, request, content = client.readData()
			if request is None:
				self.cleanup(sock, client.name)
		else:
			logger.error('client','trying to read from a client that does not exist %s' % name)
			name, peer, request, content = None, None, None, None


		return name, peer, request, content

	def sendDataBySocket(self, sock, data):
		client = self.bysock.get(sock, None)
		if client:
			res = client.writeData(data)

			if res is None:
				# close the client connection
				self.cleanup(sock, name)

				buffered, had_buffer = None, None
				result = None
			else:
				buffered, had_buffer = res
				result = buffered

			if buffered:
				if sock not in self.buffered:
					self.buffered.append(sock)
			elif had_buffer and sock in self.buffered:
				self.buffered.remove(sock)
		else:
			result = None

		return result

	def sendDataByName(self, name, data):
		client = self.byname.get(name, None)
		if client:
			res = client.writeData(data)

			if res is None:
				# close the client connection only if sendDataBySocket is not due to be called
				if client.sock not in self.buffered:
					self.cleanup(client.sock, name)

				buffered, had_buffer = None, None
				result = None
			else:
				buffered, had_buffer = res
				result = buffered

			if buffered:
				if client.sock not in self.buffered:
					self.buffered.append(client.sock)
			elif had_buffer and client.sock in self.buffered:
				self.buffered.remove(client.sock)
		else:
			result = None

		return result


	def startData(self, name, data, blockupload):
		client = self.byname.get(name, None)
		if client:
			try:
				command, d = data
			except (ValueError, TypeError):
				logger.error('client', 'invalid command sent to client %s' % name)
				self.cleanup(client.sock, name)
				res = None
			else:
				# Start checking for content sent by the client
				self.bysock[client.sock] = client

				# make sure we don't somehow end up with this still here
				self.norequest.pop(client.sock, None)

				res = client.startData(command, d, blockupload)

			if res is not None:
				buffered, had_buffer = res

				# XXX: we need to check (somewhere) that we don't read a
				#      new request here
				# buffered data we read with the HTTP headers
				name, peer, request, content = client.readData()

			else:
				# close the client connection only if sendDataBySocket is not due to be called
				if client.sock not in self.buffered:
					self.cleanup(client.sock, name)

				buffered, had_buffer = None, None
				content = None

			if buffered:
				if sock not in self.buffered:
					self.buffered.append(sock)
			elif had_buffer and sock in self.buffered:
				self.buffered.remove(sock)
		else:
			content = None

		return content



	def cleanup(self, sock, name):
		logger.debug('client','cleanup for socket %s' % sock)
		client = self.bysock.get(sock, None)
		client = client or self.norequest.get(sock, None)
		client = client or self.byname.get(name, None)
		if client:
			client.shutdown()

		self.bysock.pop(sock, None)
		self.norequest.pop(sock, None)

		self.byname.pop(name, None)
		if sock in self.buffered:
			self.buffered.remove(sock)

	def stop(self):
		for client in self.bysock.itervalues():
			client.shutdown()

		for client in self.norequest.itervalues():
			client.shutdown()

		self.bysock = {}
		self.norequest = {}
		self.byname = {}
		self.buffered = []
