#!/usr/bin/env python
# encoding: utf-8
"""
server.py

Created by David Farrar  on 2011-11-30.
Copyright (c) 2011 Exa Networks. All rights reserved.
"""

# XXX: David, please add logging here ..

import time
import socket
import errno

from .configuration import Configuration
configuration = Configuration()

from .logger import Logger,LazyFormat,hex_string,single_line
logger = Logger()

class Browser (object):
	# XXX: could eor be '\n\r\n' or the list depending on the OS - look at the RFC
	eor = '\r\n\r\n'

	def read(self, sock, read_size=4096):
		"""coroutine that reads from the socket"""

		r_buffer = ''
		r_size = yield ''

		# XXX: if the REQUEST is too big : http://tools.ietf.org/html/rfc2616#section-3.2.1
		# XXX: retun 414 (Request-URI Too Long)

		while True: # multiple requests per connection?
			buff = sock.recv(r_size or read_size) # XXX: can raise socket.error

			if not buff:  # read failed - should abord
				yield None
				return

			r_buffer += buff
			if self.eor in r_buffer: # we have a full request
				request, r_buffer = r_buffer.split(self.eor, 1)
				yield request + self.eor
				break
			yield '' # no request yet


		# our client is pipelining (or using CONNECT)
		while True:
			data = sock.recv(r_size or read_size)
			if not data:
				break
			if configuration.CONNECT:
				yield data
				continue
			yield ''
		yield None
		
	def write(self, sock):
		"""corouting that write to the socket the data it is sent"""

		w_buffer = ''
		had_buffer = False

		while True:
			data = yield len(w_buffer), had_buffer
			had_buffer = True if w_buffer else False
			w_buffer = w_buffer + data

			try:
				sent = sock.send(w_buffer)
				w_buffer = w_buffer[sent:]
			except socket.error, e:
				if e.errno in (errno.EAGAIN, errno.EINTR,errno.EWOULDBLOCK,errno.EINTR,):
					logger.server('write failed as it would have blocked (ignore), errno %s' % str(e.errno)) # XXX: wrong logger
					sent = 0
				else:
					logger.server('write failed - errno %s' % str(e.errno)) # XXX: wrong logger
					yield None,None # stop the client connection
					break # and don't come back

class Browsers (object):
	def __init__(self):
		self.factory = Browser()
		self._bysock = {}
		self._byid = {}
		self._buffered = {}
		self.cid = 1                    # A unique id per client
		self._close = set()

	def established (self):
		return list(self._bysock)

	def established_id (self):
		return list(self._byid)

	def canReply (self):
		return list(self._buffered)

	def completed (self,cid):
		# XXX: check this
		self._close.add(cid)

	def newConnection(self, sock, peer):
		"""set up the coroutines to read and write, add the new connection"""

		# XXX: wrong logger
		logger.server("new client %s" % str(peer))

		cid = self.cid
		self.cid += 1

		r = self.factory.read(sock)
		r.next()
		w = self.factory.write(sock)
		w.next()

		self._bysock[sock] = cid, r, w, peer
		self._byid[cid] = sock, r, w, peer
		self._buffered[cid] = 0

		return cid

	def readRequest(self, sock, buffer_len=0):
		cid, r, w, peer = self._bysock[sock] # raise KeyError if we gave a bad socket
		try:
			res = r.send(buffer_len)
		except socket.error,e:
			if e.errno in (errno.ECONNRESET,): # ECONNRESET : seen in real life :)
				self._close.add(cid)
				# XXX: debug
				raise
				return None,None,None
			raise

		if res is None:
			self._close.add(cid)
			return None,None,None

		return cid, peer, res

	def sendData (self, cid, data):
		logger.debug('sending data to client %d (%d)' % (cid, len(data)))
		sock, r, w, peer = self._byid[cid] # XXX: raise KeyError if we gave a bad client id, yes it does, David FIXME !

		buf_len, had_buffer = w.send(data)

		if had_buffer is None: # the socket closed
			self._close.add(cid)

		self._buffered[cid] = buf_len
		if not buf_len and self._buffered[cid]:
			self._close.add(cid)

		return buf_len

	def close (self):
		for cid in list(self._close):
			if self._buffered[cid]:
				self.sendData(cid,'')
				continue
			self.finish(cid)
			self._close.remove(cid)

	def finish (self, cid):
		logger.debug('removing client connection %d' % cid)
		sock, r, w, peer = self._byid[cid] # raise KeyError if we give a bad cliend id
		try:
			sock.shutdown(socket.SHUT_RDWR)
			sock.close()
		except socket.error:
			pass
		self._bysock.pop(sock)
		self._byid.pop(cid)
		self._buffered.pop(cid)

	def stop(self):
		logger.debug('closing all clients connections')
		for sock in self._bysock:
			try:
				sock.shutdown(socket.SHUT_RDWR)
				sock.close()
			except socket.error:
				pass
		self._bysock = {}
		self._byid = {}
		self._buffered = {}
