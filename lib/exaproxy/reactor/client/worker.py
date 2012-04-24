# encoding: utf-8
"""
server.py

Created by David Farrar  on 2011-11-30.
Copyright (c) 2011 Exa Networks. All rights reserved.
"""

import socket
import errno

from exaproxy.network.errno_list import errno_block


class Client (object):
	eor = '\r\n\r\n'
	eorn = '\n\n'

	def __init__(self, name, sock, peer, logger):
		self.name = name
		self.sock = sock
		self.peer = peer
		self.reader = self._read(sock)
		self.writer = self._write(sock)

		self.log = logger
		self.blockupload = None

		# start the _read coroutine
		self.reader.next()

	def _read(self, sock, read_size=64*1024):
		"""Coroutine managing data read from the client"""
		r_buffer = ''
		request = ''
		r_size = yield ''
		remaining = 0

		while True:
			try:
				while True:
					data = sock.recv(r_size or read_size)
					if not data:   # read failed - abort
						break

					if remaining > 0:
						length = min(len(data), remaining)
						r_size = yield '', data[:length]
						
						remaining = remaining - length
						if remaining:
							continue
						else:
							data = data[length:]

					elif remaining == -1:
						r_size = yield '', data
						continue

					r_buffer += data

					for eor in (self.eor, self.eorn):
						if eor in r_buffer:       # we have a complete request
							request, r_buffer = r_buffer.split(eor, 1)
							remaining = yield request + eor, ''  # yield to manager.readRequest
							length = min(len(r_buffer), remaining)

							if remaining > 0:
								r_size = yield '', r_buffer[:length]  # yield to manager.startData
								r_buffer = r_buffer[length:]

								remaining = remaining - length
								if not remaining:    # further data is part of a new request
									request = ''

							elif remaining == -1:
								r_size = yield '', r_buffer
								r_buffer = ''
							
							break
					else:
						r_size = yield '', ''                  # nothing seen yet
						continue

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
		res = self.reader.send(0)

		if res is not None:
			request, content = res
		else:
			request, content = None, None

		return name, peer, request, content

	def readRelated(self, remaining):
		name, peer = self.name, self.peer
		res = self.reader.send(remaining)

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

				found = True, False, 0
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
							self.log.error('Tried to send data to client after we told it to close. Dropping it.')

					if not had_buffer or data == '':
						sent = sock.send(w_buffer)
						w_buffer = w_buffer[sent:]
					else:
						sent = 0

					buffered = bool(w_buffer) or finished
					data = yield buffered, had_buffer, sent


				# break out of the outer loop as soon as we leave the inner loop
				# through normal execution
				break

			except socket.error, e:
				if e.args[0] in errno_block:
					self.log.info('interrupted when trying to sent %d bytes, will retry' % len(data))
					self.log.info('reason: errno %d: %s' % (e.args[0], errno.errorcode.get(e.args[0], '<no errno name>')))
					data = yield (True if w_buffer else False), had_buffer, 0
				else:
					self.log.critical('unexpected error writing on socket')
					self.log.critical('reason, errno %d: %s' % (e.args[0], errno.errorcode.get(e.args[0], '<no errno name>')))
					yield None # stop the client connection
					break # and don't come back

		yield None

	def writeData(self, data):
		res = self.writer.send(data)
		return res


	def startData(self, command, data):
		# start the _write coroutine
		self.writer.next()

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

	def restartData(self, command, data):
		self.writer = self._write(self.sock)
		return self.startData(command, data)

	def shutdown(self):
		try:
			self.sock.shutdown(socket.SHUT_RDWR)
			self.sock.close()
		except socket.error:
			pass

		self.writer.close()
		self.reader.close()
