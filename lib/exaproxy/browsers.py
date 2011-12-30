#!/usr/bin/env python
# encoding: utf-8
"""
server.py

Created by David Farrar  on 2011-11-30.
Copyright (c) 2011 Exa Networks. All rights reserved.
"""

# XXX: David, please add logging here ..

import socket
import errno

from .configuration import configuration
from .util.logger import logger

BLOCKING_ERRORr = (errno.EAGAIN,errno.EINTR,errno.EWOULDBLOCK,errno.EINTR)

class Browsers(object):
	eor = '\r\n\r\n'

	def __init__(self):
		self.clients = {}
		self.byname = {}
		self.buffered = []

	def _read(self, sock, read_size=16*1024):
		request = ''
		r_buffer = ''
		r_size = yield ''

		# XXX: if the REQUEST is too big : http://tools.ietf.org/html/rfc2616#section-3.2.1
		# XXX: retun 414 (Request-URI Too Long)

		while True: # multiple requests per connection?
			buff = sock.recv(r_size or read_size) # XXX can raise socket.error

			if not buff: # read failed - should abort
				yield None
				break

			# stream all data received after the request in case
			# the client is using CONNECT
			if request:
				yield buff
				continue

			r_buffer += buff

			if self.eor in r_buffer: # we have a full request
				request, r_buffer = r_buffer.split(self.eor, 1)
				yield request + self.eor
				yield r_buffer # client is using CONNECT if we are here
				r_buffer = ''
			else:
				r_size = yield '' # no request yet

	def _write(self, sock):
		"""coroutine managing data sent back to the browser"""

		# XXX:
		# TODO: use an open file for buffering data rather than storing
		#       it in memory

		w_buffer = ''
		filename = yield None

		# check to see if we are returing data directly from a local file
		# XXX: this is cleaner than using a seperate coroutine for each case?
		if filename is not None:
			try:
				# XXX: reading the file contents into memory while we have a
				# are storing buffered data in ram rather than on the filesystem
				with open(filename) as fd:
					w_buffer = fd.read()

				found = True
			except IOError:
				found = None
		else:
			found = None

		data = yield found

		while True:
			had_buffer = True if w_buffer else False
			w_buffer = w_buffer + data

			try:
				sent = sock.send(w_buffer)
			except socket.error, e:
				if e.errno in BLOCKING_ERRORS:
					logger.error('browser', 'Write failed as it would have blocked. Why were we woken up? Error %d: %s' % (e.errno, errno.errorcode.get(e.errno, '')))
					sent = 0
				else:
					yield None # stop the client connection
					break # and don't come back

			w_buffer = w_buffer[sent:]
			data = yield len(w_buffer), had_buffer


	def newConnection(self, name, sock, peer):
		# XXX: simpler code if we merge _read() and _write()
		#self.clients[sock] = name, self._run(socket)

		r = self._read(sock)
		r.next()

		w = self._write(sock)
		# starting the coroutine in startData() - helps ensure that it's called before sendData
		#w.next()

		self.clients[sock] = name, r, w, peer
		self.byname[name] = sock, r, w, peer
		return peer

	def readRequest(self, sock, buffer_len=0):
		name, r, w, peer = self.clients[sock] # raise KeyError if we gave a bad socket
		res = r.send(buffer_len)

		if res is None:
			self.cleanup(sock, name)

		return name, peer, res

	def startData(self, name, data):
		sock, r, w, peer = self.byname.get(name, EMPTY_BYNAME)
		if sock is None:
			return None

		w.next() # start the _write coroutine
		if data is None:
			return self.cleanup(sock, name)

		try:
			command, d = data
		except (ValueError, TypeError):
			logger.error('browser', 'invalid command sent to client %s' % name)
			return self.cleanup(sock, name)

		if command == 'stream':
			w.send(None) # no local file
			res = w.send(d)

			self.buffers.add(sock) # buffer immediately populated with the full local content
		elif command == 'local':
			res = w.send(d) # use local file

		if res is None:
			return self.cleanup(sock, name)

		buf_len, had_buffer = res

		if buf_len:
			self.buffers.add(sock)
		elif had_buffer and sock in self.buffers:
			self.buffers.remove(sock)

		return True



	def sendData(self, name, data):
		sock, r, w, peer = self.byname[name] # raise KeyError if we gave a bad name
		res = w.send(data)

		if res is None:
			return self.cleanup(sock, name)

		buf_len, had_buffer = res

		if buf_len:
			self.buffers.add(sock)
		elif had_buffer and sock in self.buffers:
			self.buffers.remove(sock)

		return buf_len

	def sendSocketData(self, sock, data):
		name, r, w, peer = self.clients[sock] # raise KeyError if we gave a bad name
		res = w.send(data)

		if res is None:
			return self.cleanup(sock, name)

		buf_len, had_buffer = res

		if buf_len:
			self.buffers.add(sock)
		elif had_buffer and sock in self.buffers:
			self.buffers.remove(sock)

		return buf_len

	def cleanup(self, sock, name=None):
		try:
			sock.shutdown(socket.SHUT_RDWR)
			sock.close()
		except socket.error:
			pass

		_name, _, __, ___ = self.clients.pop(sock, (None, None, None))

		if name is not None:
			self.byname.pop(name, None)

		elif _name is not None:
			self.byname.pop(_name, None)

		return None

	def shutdown(self):
		for socket in self.clients:
			try:
				sock.shutdown(socket.SHUT_RDWR)
				sock.close()
			except socket.error:
				pass

		self.clients = {}
		self.byname = {}

	# XXX: create to not change Server() too much in one go
	# XXX: do we really want this method?
	def finish(self, name):
		sock, r, w, peer = self.byname[name] # raise KeyError if we give a bad name
		print "************* IMPLEMENT ME - FINISH"
