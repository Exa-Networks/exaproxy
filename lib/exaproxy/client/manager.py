#!/usr/bin/env python
# encoding: utf-8
"""
server.py

Created by David Farrar  on 2011-11-30.
Copyright (c) 2011 Exa Networks. All rights reserved.
"""

from exaproxy.util.logger import logger
from browser import Client

class ClientManager (object):
	def __init__(self, poller):
		self.total_sent = 0L
		self.norequest = {}
		self.bysock = {}
		self.byname = {}
		self.buffered = []
		self._nextid = 0
		self.poller = poller

	def __contains__(self, item):
		return item in self.byname

	def getnextid(self):
		self._nextid += 1
		return str(self._nextid)

	def newConnection(self, sock, peer, source):
		name = self.getnextid()
		client = Client(name, sock, peer)

		self.norequest[sock] = client, source
		self.byname[name] = client

		# watch for request data becoming available to read
		self.poller.addReadSocket('opening_client', client.sock)

		logger.info('client','new id %s (socket %s) in clients : %s' % (name, sock, sock in self.bysock))
		return peer

	def readRequest(self, sock):
		"""Read only the initial HTTP headers sent by the client"""

		client, source = self.norequest.get(sock, (None, None))
		if client:
			name, peer, request, content = client.readData()
			if request:
				# headers can be read only once
				self.norequest.pop(sock, (None, None))

				# we don't care about new requests from the client
				self.poller.removeReadSocket('opening_client', client.sock)

			elif request is None:
				self.cleanup(sock, client.name)
		else:
			logger.error('client','trying to read headers from a client that does not exist %s' % sock)
			name, peer, request, content, source = None, None, None, None, None

		return name, peer, request, content, source


	def readDataBySocket(self, sock):
		client = self.bysock.get(sock, None)
		if client:
			name, peer, request, content = client.readData()
			if request:
				# Parsing of the new request will be handled asynchronously. Ensure that
				# we do not read anything from the client until a request has been sent
				# to the remote webserver. 
				# Since we just read a request, we know that the cork is not currently
				# set and so there's no risk of it being erroneously removed.
				self.poller.corkReadSocket('read_client', sock)
				
			elif request is None:
				self.cleanup(sock, client.name)
		else:
			logger.error('client','trying to read from a client that does not exist %s' % sock)
			name, peer, request, content = None, None, None, None


		return name, peer, request, content


	def readDataByName(self, name):
		client = self.byname.get(name, None)
		if client:
			name, peer, request, content = client.readData()
			if request:
				# Parsing of the new request will be handled asynchronously. Ensure that
				# we do not read anything from the client until a request has been sent
				# to the remote webserver. 
				# Since we just read a request, we know that the cork is not currently
				# set and so there's no risk of it being erroneously removed.
				self.poller.corkReadSocket('read_client', client.sock)

			elif request is None:
				self.cleanup(client.sock, name)
		else:
			logger.error('client','trying to read from a client that does not exist %s' % name)
			name, peer, request, content = None, None, None, None


		return name, peer, request, content

	def sendDataBySocket(self, sock, data):
		client = self.bysock.get(sock, None)
		if client:
			name = client.name
			res = client.writeData(data)

			if res is None:
				# close the client connection
				self.cleanup(sock, client.name)

				buffered, had_buffer,sent = None, None, 0
				result = None
				flipflop = None
			else:
				buffered, had_buffer, sent = res
				self.total_sent += sent
				result = buffered


			if buffered:
				if sock not in self.buffered:
					self.buffered.append(sock)
					flipflop = True

					# watch for the socket's send buffer becoming less than full
					self.poller.addWriteSocket('write_client', client.sock)
				else:
					flipflop = False

			elif had_buffer and sock in self.buffered:
				self.buffered.remove(sock)
				flipflop = True

				# we no longer care about writing to the client
				self.poller.removeWriteSocket('write_client', client.sock)

			else:
				flipflop = False
		else:
			result = None
			flipflop = None
			name = None

		return result, flipflop, name

	def sendDataByName(self, name, data):
		client = self.byname.get(name, None)
		if client:
			res = client.writeData(data)

			if res is None:
				# close the client connection only if sendDataBySocket is not due to be called
				if client.sock not in self.buffered:
					self.cleanup(client.sock, name)

				buffered, had_buffer, sent = None, None, 0
				#self.total_sent += sent
				result = None
				flipflop = None
			else:
				buffered, had_buffer, sent = res
				self.total_sent += sent
				result = buffered

			if buffered:
				if client.sock not in self.buffered:
					self.buffered.append(client.sock)
					flipflop = True

					# watch for the socket's send buffer becoming less than full
					self.poller.addWriteSocket('write_client', client.sock)
				else:
					flipflop = False

			elif had_buffer and client.sock in self.buffered:
				self.buffered.remove(client.sock)
				flipflop = True

				# we no longer care about writing to the client
				self.poller.removeWriteSocket('write_client', client.sock)

			else:
				flipflop = False
		else:
			result = None
			flipflop = None

		return result, flipflop


	def startData(self, name, data, remaining):
		client = self.byname.get(name, None)
		if client:
			try:
				command, d = data
			except (ValueError, TypeError):
				logger.error('client', 'invalid command sent to client %s' % name)
				self.cleanup(client.sock, name)
				res = None
			else:
				if client.sock not in self.bysock:
					# Start checking for content sent by the client
					self.bysock[client.sock] = client

					# watch for the client sending new data
					self.poller.addReadSocket('read_client', client.sock)

					# make sure we don't somehow end up with this still here
					self.norequest.pop(client.sock, (None,None))

					# NOTE: always done already in readRequest
					self.poller.removeReadSocket('opening_client', client.sock)
					res = client.startData(command, d)

				else:
					res = client.restartData(command, d)

					# If we are here then we must have prohibited reading from the client
					# and it must otherwise have been in a readable state
					self.poller.uncorkReadSocket('read_client', client.sock)



			if res is not None:
				buffered, had_buffer, sent = res

				# buffered data we read with the HTTP headers
				name, peer, request, content = client.readRelated(remaining)
				if request:
					logger.error('client', 'reading multiple requests')
					self.cleanup(client.sock, name)
					buffered, had_buffer = None, None
					content = None

				elif request is None:
					self.cleanup(client.sock, name)

			else:
				# close the client connection only if sendDataBySocket is not due to be called
				if client.sock not in self.buffered:
					self.cleanup(client.sock, name)

				buffered, had_buffer = None, None
				content = None

			if buffered:
				if client.sock not in self.buffered:
					self.buffered.append(client.sock)

					# watch for the socket's send buffer becoming less than full
					self.poller.addWriteSocket('write_client', client.sock)

			elif had_buffer and client.sock in self.buffered:
				self.buffered.remove(client.sock)

				# we no longer care about writing to the client
				self.poller.removeWriteSocket('write_client', client.sock)
		else:
			content = None

		return content


	def corkUploadByName(self, name):
		client = self.byname.get(name, None)
		if client:
			self.poller.corkReadSocket('read_client', client.sock)

	def uncorkUploadByName(self, name):
		client = self.byname.get(name, None)
		if client:
			if client.sock in self.bysock:
				self.poller.uncorkReadSocket('read_client', client.sock)

	def cleanup(self, sock, name):
		logger.debug('client','cleanup for socket %s' % sock)
		client = self.bysock.get(sock, None)
		client, source = (client,None) or self.norequest.get(sock, (None,None))
		client = client or self.byname.get(name, None)

		self.bysock.pop(sock, None)
		self.norequest.pop(sock, (None,None))

		if client:
			self.poller.removeWriteSocket('write_client', client.sock)
			self.poller.removeReadSocket('read_client', client.sock)
			self.poller.removeReadSocket('opening_client', client.sock)
	
			client.shutdown()


		self.byname.pop(name, None)
		if sock in self.buffered:
			self.buffered.remove(sock)

	def stop(self):
		for client in self.bysock.itervalues():
			client.shutdown()

		for client, source in self.norequest.itervalues():
			client.shutdown()

		self.poller.clearRead('read_client')
		self.poller.clearRead('opening_client')
		self.poller.clearWrite('write_client')

		self.bysock = {}
		self.norequest = {}
		self.byname = {}
		self.buffered = []
