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



class Client(object):
	eor = '\r\n\r\n'

	def __init__(self, name, sock, peer):
		self.name = name
		self.sock = sock
		self.peer = peer
		self.reader = self._read(sock)
		self.writer = self._write(sock)

		self.blockupload = None

		# start the _read coroutine
		self.reader.next()


	def _read(self, sock, read_size=64*1024):
		"""Coroutine managing data read from the client"""
		r_buffer = ''
		request = ''
		r_size = yield ''

		while True:
			try:
				while True:
					data = sock.recv(r_size or read_size)
					if not data:   # read failed - abort
						break

					if request:
						r_size = yield '', data                
						continue

					r_buffer += data

					if self.eor in r_buffer:       # we have a complete request
						request, r_buffer = r_buffer.split(self.eor, 1)

						r_size = yield request + self.eor, ''  # yield to manager.readRequest
						r_size = yield '', r_buffer            # yield to manager.startData
						r_buffer = ''
					else:
						r_size = yield '', ''                  # nothing seen yet

				# break out of the outer loop as soon as we leave the inner loop
				# through normal execution
				break

			except socket.error, e:
				if e.args[0] in errno_block:
					yield '', ''
				else:
					break

		yield None

	def readData(self):
		name, peer = self.name, self.peer
		res = self.reader.send(0) if self.reader else None

		if res is not None:
			request, content = res
		else:
			request, content = None, None

		return name, peer, request, content



	def _write(self, sock):
		"""Coroutine managing data sent to the client"""
		
		w_buffer = ''
		filename = yield None

		# check to see if we are returning data directly from a local file
		if filename is not None:
			try:
				# XXX: we must read from the file on demand rather than doing this
				with open(filename) as fd:
					w_buffer = fd.read()

				found = True, False
			except IOError:
				found = None

			data = yield found
			w_buffer = data + w_buffer
		else:
			found = None

		data = yield found
		finished = False

		while True:
			try:
				while True:
					had_buffer = bool(w_buffer)

					if data is not None:
						w_buffer += data
					else:
						# We've finished downloading, even if the client hasn't yet
						finished = True

					if finished:
						if not w_buffer:
							break      # terminate the client connection
						elif data:
							logger.error('client', 'Tried to send data to client after we told it to close. Dropping it.')

					if not had_buffer or data == '':
						sent = sock.send(w_buffer)
						logger.info('client', 'wrote to socket %s sent %d bytes' % (str(sock),sent))
						w_buffer = w_buffer[sent:]

					buffered = bool(w_buffer) or finished
					data = yield buffered, had_buffer


				# break out of the outer loop as soon as we leave the inner loop
				# through normal execution
				break

			except socket.error, e:
				if e.args[0] in errno_block:
					logger.error('client','failed to sent %d bytes' % len(data))
					logger.error('client','it would have blocked, why were we woken up !?!')
					logger.error('client','error %d: %s' % (e.args[0], errno.errorcode.get(e.args[0], '')))
					data = yield (True if w_buffer else False), had_buffer
				else:
					logger.critical('client','????? ARRGH ?????')
					yield None # stop the client connection
					break # and don't come back

		yield None

	def writeData(self, data):
		if self.blockupload:
			if self.reader:
				self.reader.send(None)
				self.reader = None

		res = self.writer.send(data)
		return res


	def startData(self, command, data, blockupload):
		# start the _write coroutine
		self.writer.next()

		self.blockupload = blockupload

		if command == 'stream':
			self.writer.send(None)  # no local file
			res = self.writer.send(data)

		elif command == 'close':
			self.writer.send(None)  # no local file
			self.writer.send(data)
			res = self.writer.send(None)  # close the connection once the buffer is empty

		elif command == 'file':
			header, filename = data
			res = self.writer.send(filename)  # use local file
			self.writer.send(header)      # write the response headers before the file
			
			self.writer.send(None)        # close the connection once the buffer is empty
		else:
			res = None

		# buffered, had_buffer
		return res



	def shutdown(self):
		try:
			self.sock.shutdown(socket.SHUT_RDWR)
			self.sock.close()
		except socket.error:
			pass

		self.writer.close()
		if self.reader:
			self.reader.close()
