# encoding: utf-8
"""
manager.py

Created by David Farrar  on 2011-11-30.
Copyright (c) 2011-2013  Exa Networks. All rights reserved.
"""

from exaproxy.util.log.logger import Logger
from exaproxy.util.cache import TimeCache
from .worker import Client

from exaproxy.htmuttp.proxy import ProxyProtocol

class ClientManager (object):
	unproxy = ProxyProtocol().parseRequest

	def __init__(self, poller, configuration):
		self.total_sent4 = 0L
		self.total_sent6 = 0L
		self.total_requested = 0L
		self.norequest = TimeCache(configuration.http.idle_connect)
		self.bysock = {}
		self.byname = {}
		self.buffered = []
		self._nextid = 0
		self.poller = poller
		self.log = Logger('client', configuration.log.client)
		self.proxied = configuration.http.proxied
		self.max_buffer = configuration.http.header_size

	def __contains__(self, item):
		return item in self.byname

	def getnextid(self):
		self._nextid += 1
		return str(self._nextid)

	def expire (self,number=100):
		count = 0
		for sock in self.norequest.expired(number):
			client = self.norequest.get(sock,[None,])[0]
			if client:
				self.cleanup(sock,client.name)
				count += 1

		return count

	def newConnection(self, sock, peer, source):
		name = self.getnextid()
		client = Client(name, sock, peer, self.log, self.max_buffer)

		self.norequest[sock] = client, source
		self.byname[name] = client, source

		# watch for the opening request
		self.poller.addReadSocket('opening_client', client.sock)

		#self.log.info('new id %s (socket %s) in clients : %s' % (name, sock, sock in self.bysock))
		return peer

	def readRequest(self, sock):
		"""Read only the initial HTTP headers sent by the client"""

		client, source = self.norequest.get(sock, (None, None))
		if client:
			name, peer, request, content = client.readData()
			if request:
				self.total_requested += 1
				# headers can be read only once
				self.norequest.pop(sock, (None, None))

				# we have now read the client's opening request
				self.poller.removeReadSocket('opening_client', client.sock)

			elif request is None:
				self.cleanup(sock, client.name)
		else:
			self.log.error('trying to read headers from a client that does not exist %s' % sock)
			name, peer, request, content, source = None, None, None, None, None

		if request and self.proxied is True:
			client_ip, client_request = self.unproxy(request)

			if client_ip and client_request:
				peer = client_ip
				request = client_request
				client.setPeer(client_ip)

		return name, peer, request, content, source


	def readDataBySocket(self, sock):
		client, source = self.bysock.get(sock, (None, None))
		if client:
			name, peer, request, content = client.readData()
			if request:
				self.total_requested += 1
				# Parsing of the new request will be handled asynchronously. Ensure that
				# we do not read anything from the client until a request has been sent
				# to the remote webserver.
				# Since we just read a request, we know that the cork is not currently
				# set and so there's no risk of it being erroneously removed.
				self.poller.corkReadSocket('read_client', sock)

			elif request is None:
				self.cleanup(sock, client.name)
		else:
			self.log.error('trying to read from a client that does not exist %s' % sock)
			name, peer, request, content = None, None, None, None


		return name, peer, request, content, source


	def readDataByName(self, name):
		client, source = self.byname.get(name, (None, None))
		if client:
			name, peer, request, content = client.readData()
			if request:
				self.total_requested += 1
				# Parsing of the new request will be handled asynchronously. Ensure that
				# we do not read anything from the client until a request has been sent
				# to the remote webserver.
				# Since we just read a request, we know that the cork is not currently
				# set and so there's no risk of it being erroneously removed.
				self.poller.corkReadSocket('read_client', client.sock)

			elif request is None:
				self.cleanup(client.sock, name)
		else:
			self.log.error('trying to read from a client that does not exist %s' % name)
			name, peer, request, content = None, None, None, None


		return name, peer, request, content

	def sendDataBySocket(self, sock, data):
		client, source = self.bysock.get(sock, (None, None))
		if client:
			name = client.name
			res = client.writeData(data)

			if res is None:
				# close the client connection
				self.cleanup(sock, client.name)

				buffered, had_buffer, sent4, sent6 = None, None, 0, 0
				result = None
				buffer_change = None
			else:
				buffered, had_buffer, sent4, sent6 = res
				self.total_sent4 += sent4
				self.total_sent6 += sent6
				result = buffered


			if buffered:
				if sock not in self.buffered:
					self.buffered.append(sock)
					buffer_change = True

					# watch for the socket's send buffer becoming less than full
					self.poller.addWriteSocket('write_client', client.sock)
				else:
					buffer_change = False

			elif had_buffer and sock in self.buffered:
				self.buffered.remove(sock)
				buffer_change = True

				# we no longer care about writing to the client
				self.poller.removeWriteSocket('write_client', client.sock)

			else:
				buffer_change = False
		else:
			result = None
			buffer_change = None
			name = None

		return result, buffer_change, name, source

	def sendDataByName(self, name, data):
		client, source = self.byname.get(name, (None, None))
		if client:
			res = client.writeData(data)

			if res is None:
				# we cannot write to the client so clean it up
				self.cleanup(client.sock, name)

				buffered, had_buffer, sent4, sent6 = None, None, 0, 0
				result = None
				buffer_change = None
			else:
				buffered, had_buffer, sent4, sent6 = res
				self.total_sent4 += sent4
				self.total_sent6 += sent6
				result = buffered

			if buffered:
				if client.sock not in self.buffered:
					self.buffered.append(client.sock)
					buffer_change = True

					# watch for the socket's send buffer becoming less than full
					self.poller.addWriteSocket('write_client', client.sock)
				else:
					buffer_change = False

			elif had_buffer and client.sock in self.buffered:
				self.buffered.remove(client.sock)
				buffer_change = True

				# we no longer care about writing to the client
				self.poller.removeWriteSocket('write_client', client.sock)

			else:
				buffer_change = False
		else:
			result = None
			buffer_change = None

		return result, buffer_change, client


	def startData(self, name, data, remaining):
		# NOTE: soo ugly but fast to code
		nb_to_read = 0
		if type(remaining) == type(''):
			if 'chunked' in remaining:
				mode = 'chunked'
		elif remaining > 0:
			mode = 'transfer'
			nb_to_read = remaining
		elif remaining == 0:
			mode = 'request'
		else:
			mode = 'passthrough'

		client, source = self.byname.get(name, (None, None))
		if client:
			try:
				command, d = data
			except (ValueError, TypeError):
				self.log.error('invalid command sent to client %s' % name)
				self.cleanup(client.sock, name)
				res = None
			else:
				if client.sock not in self.bysock:
					# Start checking for content sent by the client
					self.bysock[client.sock] = client, source

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
				buffered, had_buffer, sent4, sent6 = res

				# buffered data we read with the HTTP headers
				name, peer, request, content = client.readRelated(mode,nb_to_read)
				if request:
					self.total_requested += 1
					self.log.info('reading multiple requests')
					self.cleanup(client.sock, name)
					buffered, had_buffer = None, None
					content = None

				elif request is None:
					self.cleanup(client.sock, name)
					buffered, had_buffer = None, None
					content = None

			else:
				# we cannot write to the client so clean it up
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

		return client, content, source


	def corkUploadByName(self, name):
		client, source = self.byname.get(name, (None, None))
		if client:
			self.poller.corkReadSocket('read_client', client.sock)

	def uncorkUploadByName(self, name):
		client, source = self.byname.get(name, (None, None))
		if client:
			if client.sock in self.bysock:
				self.poller.uncorkReadSocket('read_client', client.sock)

	def cleanup(self, sock, name):
		self.log.debug('cleanup for socket %s' % sock)
		client, source = self.bysock.get(sock, (None,None))
		client, source = (client,None) if client else self.norequest.get(sock, (None,None))
		client, source = (client,None) or self.byname.get(name, (None,None))

		self.bysock.pop(sock, None)
		self.norequest.pop(sock, (None,None))
		self.byname.pop(name, None)

		if client:
			self.poller.removeWriteSocket('write_client', client.sock)
			self.poller.removeReadSocket('read_client', client.sock)
			self.poller.removeReadSocket('opening_client', client.sock)

			client.shutdown()
		else:
			self.log.error('COULD NOT CLEAN UP SOCKET %s' % sock)

		if sock in self.buffered:
			self.buffered.remove(sock)

	def softstop (self):
		if len(self.byname) > 0 or len(self.norequest) > 0:
			return False
		self.log.critical('no more client connection, exiting.')
		return True

	def stop(self):
		for client, source in self.bysock.itervalues():
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
