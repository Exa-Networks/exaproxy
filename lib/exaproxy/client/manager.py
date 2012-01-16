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

from exaproxy.network.poller import errno_block
from exaproxy.util.logger import logger

class ClientManager (object):
	eor = '\r\n\r\n'

	def __init__(self):
		self.bysock = {}
		self.byname = {}
		self.buffered = []

	def __contains__(self, item):
		return item in self.byname

	def _read(self, sock, read_size=16*1024):
		request = ''
		r_buffer = ''
		r_size = yield ''

		# XXX: if the REQUEST is too big : http://tools.ietf.org/html/rfc2616#section-3.2.1
		# XXX: retun 414 (Request-URI Too Long)

		while True:
			try:
				while True: # multiple requests per connection?
					logger.info('client', 'reading socket %s' % str(sock))
					buff = sock.recv(r_size or read_size) # XXX can raise socket.error
					logger.info('client', 'reading socket %s done, have %d bytes' % (str(sock),len(buff)))

					if not buff: # read failed - should abort
						break

					# stream all data received after the request in case
					# the client is using CONNECT
					if request:
						yield '', buff
						continue

					r_buffer += buff

					if self.eor in r_buffer: # we have a full request
						request, r_buffer = r_buffer.split(self.eor, 1)
						yield request + self.eor, ''
						yield '', r_buffer # client is using CONNECT if we are here
						r_buffer = ''
					else:
						r_size = yield '', '' # no request yet

				break
			except socket.error, e:
				if e.errno in errno_block:
					yield '', ''
				else:
					break

		yield None

	def _write(self, sock):
		"""coroutine managing data sent back to the client"""

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

				found = True, False
			except IOError:
				found = None
		else:
			found = None

		data = yield found
		finished = False

		while True:
			try:
				while True:
					had_buffer = True if w_buffer else False

					if data is not None:
						w_buffer = w_buffer + data
					else:
						# we've finished downloading, even if the client hasn't yet
						finished = True


					if finished:
						if data:
							logger.error('client', '*'*80 + 'Tried to send data to client after we told it to close. Dropping it.')
							continue

						if not w_buffer:
							break    # stop the client connection

					if not had_buffer or data == '':
						sent = sock.send(w_buffer)
						logger.info('client', 'wrote to socket %s sent %d bytes' % (str(sock),sent))
						w_buffer = w_buffer[sent:]

					data = yield (True if w_buffer else False), had_buffer

				# break out of the outer loop as soon as we leave the inner loop
				# through normal execution
				break

			except socket.error, e:
				if e.errno in errno_block:
					logger.error('client','failed to sent %d bytes' % len(data))
					logger.error('client','it would have blocked, why were we woken up !?!')
					logger.error('client','error %d: %s' % (e.errno, errno.errorcode.get(e.errno, '')))
					data = yield (True if w_buffer else False), had_buffer
				else:
					logger.critical('client','????? ARRGH ?????')
					yield None # stop the client connection
					break # and don't come back

		yield None


	def newConnection(self, name, sock, peer):
		# XXX: simpler code if we merge _read() and _write()
		#self.bysock[sock] = name, self._run(socket)

		r = self._read(sock)
		r.next()

		w = self._write(sock)
		# starting the coroutine in startData() - helps ensure that it's called before sendData
		#w.next()

		self.bysock[sock] = name, r, w, peer
		self.byname[name] = sock, r, w, peer

		logger.info('client','new id %s (socket %s) in clients : %s' % (name, sock, sock in self.bysock))
		return peer

	def readRequestBySocket(self, sock, buffer_len=0):
		name, r, w, peer = self.bysock.get(sock, (None, None, None, None)) # raise KeyError if we gave a bad socket

		if name is None:
			logger.error('client','trying to read from a client that does not exists %s' % sock)
			return None

		res = r.send(buffer_len)

		if res is not None:
			request, extra = res
		else:
			self.cleanup(sock, name)
			request = None
			extra = None

		return name, peer, request, extra

	def readRequestByName(self, name, buffer_len=0):
		sock, r, w, peer = self.byname.get(name, (None, None, None, None)) # raise KeyError if we gave a bad socket

		if sock is None:
			logger.error('client','trying to read request from a client that does not exists %s' % sock)
			return None

		res = r.send(buffer_len)

		if res is not None:
			request, extra = res
		else:
			self.cleanup(sock, name)
			request = None
			extra = None

		return name, peer, request, extra

	def startData(self, name, data):
		sock, r, w, peer = self.byname.get(name, (None, None, None))
		if sock is None:
			return None

		w.next() # start the _write coroutine
		if data is None:
			logger.info('client','terminating client %s before it could begin %s' % (name, sock))
			return self.cleanup(sock, name)

		try:
			command, d = data
		except (ValueError, TypeError):
			logger.error('client', 'invalid command sent to client %s' % name)
			return self.cleanup(sock, name)

		if command == 'stream':
			w.send(None) # no local file
			res = w.send(d)

		elif command == 'html':
			w.send(None) # no local file
			w.send(d)
			res = w.send(None)

		elif command == 'file':
			res = w.send(d) # use local file
			w.send(None)    # close the connection once our buffer is empty
			self.buffered.append(sock) # buffer immediately populated with the full local content
			return 

		if res is None:
			# XXX: this is messy
			# do not clean up the socket if we know it is still referenced
			if sock not in self.buffered:
				return self.cleanup(sock, name)

		buf_len, had_buffer = res

		if buf_len:
			self.buffered.append(sock)
		elif had_buffer and sock in self.buffered:
			self.buffered.remove(sock)

		return True



	def sendDataByName(self, name, data):
		sock, r, w, peer = self.byname.get(name, (None, None, None, None)) # raise KeyError if we gave a bad name
		if sock is None:
			logger.error('client','trying to send data using an id that does not exists %s' % name)
			return None

		logger.info('client','sending %s bytes to client %s: %s' % (len(data) if data is not None else None, name, sock))
		res = w.send(data)

		if res is None:
			# XXX: this is messy
			# do not clean up the socket if we know it is still referenced
			if sock not in self.buffered:
				return self.cleanup(sock, name)
			return None

		buf_len, had_buffer = res

		if buf_len:
			if sock not in self.buffered:
				self.buffered.append(sock)
		elif had_buffer and sock in self.buffered:
			self.buffered.remove(sock)

		return buf_len

	def sendDataBySocket(self, sock, data):
		name, r, w, peer = self.bysock.get(sock, (None, None, None, None)) # raise KeyError if we gave a bad name
		if name is None:
			logger.error('client','trying to send data using an socket that does not exists %s %s %s' % (sock,type(data),data))
			return None

		res = w.send(data)
		logger.info('client','flushing data to %s: %s' % (name, sock))

		if res is None:
			if sock in self.buffered:
				self.buffered.remove(sock)
			return self.cleanup(sock, name)

		buf_len, had_buffer = res

		if buf_len:
			if sock not in self.buffered:
				self.buffered.append(sock)
		elif had_buffer and sock in self.buffered:
			self.buffered.remove(sock)

		return buf_len

	def cleanup(self, sock, name=None):
		logger.debug('client','cleanup for socket %s' % sock)
		try:
			sock.shutdown(socket.SHUT_RDWR)
			sock.close()
		except socket.error:
			pass

		_name, _, __, ___ = self.bysock.pop(sock, (None, None, None))

		if name is not None:
			self.byname.pop(name, None)

		elif _name is not None:
			self.byname.pop(_name, None)

		return None

	def shutdown(self):
		for socket in self.bysock:
			try:
				sock.shutdown(socket.SHUT_RDWR)
				sock.close()
			except socket.error:
				pass

		self.bysock = {}
		self.byname = {}

	# XXX: create to not change Server() too much in one go
	# XXX: do we really want this method?
	def finish(self, name):
		sock, r, w, peer = self.byname[name] # raise KeyError if we give a bad name
		#XXX: Fixme
		print "************* IMPLEMENT ME - FINISH"
		pass

	def stop (self):
		#XXX: Fixme
		print "JUST HERE TO NOT HAVE ERRORS"
		pass
		