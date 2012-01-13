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

BLOCKING_ERRORS = (errno.EAGAIN,errno.EINTR,errno.EWOULDBLOCK,errno.EINTR)

class Browsers(object):
	eor = '\r\n\r\n'

	def __init__(self):
		self.clients = {}
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
					print "READING FROM BROWSER: %s" % sock
					buff = sock.recv(r_size or read_size) # XXX can raise socket.error
					print "READ %s BYTES FROM BROWSER: %s" % (len(buff), sock)

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
				if e.errno in BLOCKING_ERRORS:
					yield '', ''
				else:
					break

		yield None

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
							logger.error('browser', '*'*80 + 'Tried to send data to browser after we told it to close. Dropping it.')
							continue

						if not w_buffer:
							break    # stop the client connection

					if not had_buffer or data == '':
						sent = sock.send(w_buffer)
						print "SENT %s BYTES OF DATA TO BROWSER: %s" % (sent, sock)
						w_buffer = w_buffer[sent:]

					data = yield (True if w_buffer else False), had_buffer

				# break out of the outer loop as soon as we leave the inner loop
				# through normal execution
				break

			except socket.error, e:
				if e.errno in BLOCKING_ERRORS:
					logger.error('browser', 'Write failed as it would have blocked. Why were we woken up? Error %d: %s' % (e.errno, errno.errorcode.get(e.errno, '')))
					print "DATA TO SEND WAS", len(data)
					data = yield (True if w_buffer else False), had_buffer
				else:
					print "????? ARRGH ?????"
					yield None # stop the client connection
					break # and don't come back

		yield None


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

		print "NEW BROWSER HAS ID %s: %s %s" % (name, sock, sock in self.clients)
		return peer

	def readSocketRequest(self, sock, buffer_len=0):
		name, r, w, peer = self.clients.get(sock, (None, None, None, None)) # raise KeyError if we gave a bad socket

		if name is None:
			print "TRYING TO READ FROM A CLIENT THAT DOES NOT EXIST", sock
			return None

		res = r.send(buffer_len)

		if res is not None:
			request, extra = res
		else:
			self.cleanup(sock, name)
			request = None
			extra = None

		return name, peer, request, extra

	def readRequest(self, name, buffer_len=0):
		sock, r, w, peer = self.byname.get(name, (None, None, None, None)) # raise KeyError if we gave a bad socket

		if sock is None:
			print "TRYING TO READ FROM A CLIENT THAT DOES NOT EXIST", name
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
			print "TERMINATING CLIENT %s BEFORE IT COULD BEGIN: %s" % (name, sock)
			return self.cleanup(sock, name)

		try:
			command, d = data
		except (ValueError, TypeError):
			logger.error('browser', 'invalid command sent to client %s' % name)
			print "******* INVALID COMMAND SO CLEANING UP CLIENT"
			return self.cleanup(sock, name)

		if command == 'stream':
			w.send(None) # no local file
			res = w.send(d)

		elif command == 'data':
			w.send(None) # no local file
			w.send(d)
			res = w.send(None)

		elif command == 'local':
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



	def sendData(self, name, data):
		sock, r, w, peer = self.byname.get(name, (None, None, None, None)) # raise KeyError if we gave a bad name
		if sock is None:
			print "TRYING TO SEND DATA USING AN ID THAT DOES NOT EXIST:", name
			return None


		print "SENDING %s BYTES OF DATA TO BROWSER %s: %s" % (len(data) if data is not None else None, name, sock)
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

	def sendSocketData(self, sock, data):
		name, r, w, peer = self.clients.get(sock, (None, None, None, None)) # raise KeyError if we gave a bad name
		if name is None:
			print "TRYING TO SEND DATA TO A SOCKET THAT DOES NOT EXIST:", sock, type(data), data
			return None

		res = w.send(data)
		print "FLUSHING DATA TO %s: %s" % (name, sock)

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
		print "CLEANUP " * 10
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
