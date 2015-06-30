# encoding: utf-8
"""
server.py

Created by David Farrar  on 2011-11-30.
Copyright (c) 2011-2013  Exa Networks. All rights reserved.
"""

import socket
import errno

from exaproxy.network.functions import isipv4
from exaproxy.network.errno_list import errno_block

def ishex (s):
	return bool(s) and not bool(s.strip('0123456789abcdefABCDEF'))

def count_quotes (data):
	return data.count('"') - data.count('\\"')

class ICAPClient (object):
	eor = ['\r\n\r\n', '\n\n']
	eol = ['\r\n', '\n']

	__slots__ = ['name', 'ipv4', 'sock', 'peer', 'reader', 'writer', 'w_buffer', 'log']

	def __init__(self, name, sock, peer, logger, max_buffer):
		self.name = name
		self.ipv4 = isipv4(sock.getsockname()[0])
		self.sock = sock
		self.peer = peer
		self.reader = self._read(sock,max_buffer)
		self.writer = self._write(sock)
		self.w_buffer = ''
		self.log = logger

		# start the _read coroutine
		self.reader.next()

	def checkRequest (self, r_buffer, size, seek=0):
		for eor in self.eor:
			pos = r_buffer[seek:].find(eor)
			if pos == -1: continue

			buff = r_buffer[:seek+pos]
			if not buff: continue

			if not count_quotes(buff) % 2:  # we have matching pairs
				return buff + eor, r_buffer[seek+pos+len(eor):], 0

			seek += pos + len(eor)

		if size and len(r_buffer) > size:
			return None,None,None

		return '', r_buffer, seek


	def checkChunkSize (self, r_buffer):
		# return a tuple : bool, length
		# * the bool is : is there more chunk to come
		# * the len contains the size of the chunk(s) extracted
		#   a size of None means that we could not decode as it is invalid

		total_len = 0

		while r_buffer:
			if not '\n' in r_buffer:
				if len(r_buffer) > 6:  # len('FFFF') + len(\r\n)
					return True, None
				return True, 0

			header,r_buffer = r_buffer.split('\n', 1)
			len_header = len(header) + 1

			if header.endswith('\r'):
				header = header[:-1]
				len_eol = 2
			else:
				len_eol = 1

			if ';' in header:
				header = header.split(';',1)[0]

			if not ishex(header):
				return True,None

			len_chunk = int(header, 16)

			# 0xFFFF is not enough - coad is complaining :p
			if len_chunk > 0x100000:
				return True,None

			if len_chunk == 0:
				total_len += len_header
				return False, total_len
			else:
				total = len_chunk + len_eol
				total_len += total + len_header
				r_buffer = r_buffer[total:]

		return True,total_len


	def _read (self, sock, max_buffer, read_size=64*1024):
		"""Coroutine managing data read from the client"""
		# yield request, content
		# request is the text that form the request header
		# content any text which is related to the current request after the headers

		yield ''

		r_buffer = ''
		processing = False
		nb_to_send = 0
		seek = 0

		# mode can be one of : request, chunk, extension, relay
		# icap : we are reading the icap headers
		# request : we are reading the request (read all you can until a separator)
		# extra-headers : we are reading data until a separator
		# chunked : we are reading chunk-encoded data
		# transfer : we are reading as much as requested in remaining
		# passthrough : read as much as can to be relayed

		mode = 'icap'
		icap_request = ''
		http_request = ''

		while True:
			try:
				while True:
					if processing is False:
						new_data = sock.recv(read_size)
						if not new_data:
							break # read failed so we abort
					else:
						processing = False

					r_buffer += new_data

					if mode in ('icap', 'request'):
						if mode == 'icap':
							# ignore EOL
							r_buffer = r_buffer.lstrip('\r\n')

							# check to see if we have read an entire request
							icap_request, r_buffer, seek = self.checkRequest(r_buffer, max_buffer, seek)

							if icap_request:
								mode = 'request'
								seek = 0

						if mode == 'request':
							# check to see if we have read an entire request
							http_request, r_buffer, seek = self.checkRequest(r_buffer, max_buffer, seek)

						if http_request:
							icap_request = [icap_request]
							http_request = [http_request]
							seek = 0

							mode, nb_to_send = yield icap_request, http_request, ['']

						elif icap_request is not None:
							yield [''], [''], ['']
							continue

						else:
							break

					if mode not in ('icap', 'request'):
						# all modes that are not directly related to reading a new request
						data, r_buffer, mode, nb_to_send, seek = self.process(r_buffer, mode, nb_to_send, max_buffer, seek)
						if data is None:
							break

						# stream data to the remote server
						data = [data]
						yield [''], [''], data

					if mode == 'icap':
						processing = True if r_buffer else False

				# break out of the outer loop as soon as we leave the inner loop
				# through normal execution
				break

			except socket.error, e:
				if e.args[0] in errno_block:
					yield [''], [''], ['']

				else:
					break

		yield [None], [None], [None]

	def process (self, r_buffer, mode, nb_to_send, max_buffer, seek):
		if mode == 'transfer':
			_, r_buffer, new_mode, new_to_send, seek = self._transfer(r_buffer, mode, nb_to_send)
			data = ''

		elif mode == 'chunked':
			_, r_buffer, new_mode, new_to_send, seek = self._chunked(r_buffer, mode, nb_to_send)
			data = ''

		else:
			self.log.error('The programmers are monkeys - please give them bananas ..')
			self.log.error('the mode was spelled : [%s]' % mode)
			data, r_buffer, new_mode, new_to_send, seek = None, None, None, None, 0

		if new_mode == 'transfer' and mode != 'transfer':
			_, r_buffer, new_mode, new_to_send, seek = self._transfer(r_buffer, new_mode, new_to_send)

		return data, r_buffer, new_mode, new_to_send, seek

	def _transfer (self, r_buffer, mode, nb_to_send):
		r_len = len(r_buffer)
		length = min(r_len, nb_to_send)

		r_buffer, data = r_buffer[length:], r_buffer[:length]
		nb_to_send = nb_to_send - length

		if nb_to_send == 0:
			mode = 'icap'

		return data, r_buffer, mode, nb_to_send, 0

	def _chunked (self, r_buffer, mode, nb_to_send):
		r_len = len(r_buffer)
		length = min(r_len, nb_to_send)

		if nb_to_send >= r_len:
			r_buffer, data = r_buffer[length:], r_buffer[:length]
			nb_to_send = nb_to_send - length

		else:
			data = ''

		# sum of the sizes of all chunks in our buffer
		chunked, new_to_send = self.checkChunkSize(r_buffer[nb_to_send:])

		if new_to_send is not None:
			nb_to_send += new_to_send

		else:
			# could not read any chunk (data is invalid)
			data = None

		if not chunked:
			mode = 'transfer' if nb_to_send > 0 else 'icap'

		return data, r_buffer, mode, nb_to_send, 0

	def setPeer (self, peer):
		"""Set the claimed ip address for this client.
		Does not effect the ip address we try sending data to."""
		self.peer = peer

	def readData(self):
		# pop data from lists to free memory held by the coroutine
		icap_header_l, http_header_l, content_l = self.reader.send(('',0))
		icap_header = icap_header_l.pop()
		http_header = http_header_l.pop()
		content = content_l.pop()
		return self.name, self.peer, icap_header, http_header, content

	def readRelated(self, mode, remaining):
		# pop data from lists to free memory held by the coroutine
		mode = mode or 'icap'
		icap_header_l, http_header_l, content_l = self.reader.send((mode,remaining))
		icap_header = icap_header_l.pop()
		http_header = http_header_l.pop()
		content = content_l.pop()
		return self.name, self.peer, icap_header, http_header, content

	def _write(self, sock):
		"""Coroutine managing data sent to the client"""
		filename = yield None

		# check to see if we are returning data directly from a local file
		if filename is not None:
			try:
				# NOTE: we must read from the file on demand rather than doing this
				with open(filename) as fd:
					self.w_buffer += fd.read()

				found = True, False, 0, 0
			except IOError:
				found = None

			data = yield found
			self.w_buffer = data + self.w_buffer
		else:
			found = None

		data = yield found
		finished = False
		w_buffer = self.w_buffer

		while True:
			try:
				while True:
					w_buffer = self.w_buffer
					had_buffer = bool(w_buffer)

					if data is not None:
						w_buffer += data
					else:
						# We've finished downloading, even if the client hasn't yet
						finished = True

					if finished:
						if not w_buffer:
							break	  # terminate the client connection
						elif data:
							self.log.error('Tried to send data to client after we told it to close. Dropping it.')

					if not had_buffer or data == '':
						sent = sock.send(w_buffer)
						#if sent:
						#	self.log.debug(">> [%s]" % w_buffer[:sent].replace('\t','\\t').replace('\r','\\r').replace('\n','\\n'))
						w_buffer = w_buffer[sent:]
					else:
						sent = 0

					self.w_buffer = w_buffer
					buffered = bool(w_buffer) or finished
					data = yield buffered, had_buffer, sent if self.ipv4 else 0, 0 if self.ipv4 else sent

				# break out of the outer loop as soon as we leave the inner loop
				# through normal execution
				yield None
				break

			except socket.error, e:
				self.w_buffer = w_buffer
				if e.args[0] in errno_block:
					self.log.debug('interrupted when trying to sent %d bytes, fine, will retry' % len(data))
					self.log.debug('reason: errno %d: %s' % (e.args[0], errno.errorcode.get(e.args[0], '<no errno name>')))
					data = yield bool(w_buffer) or finished, had_buffer, 0, 0
				else:
					self.log.debug('handled an unexpected error writing on socket')
					self.log.debug('reason, errno %d: %s' % (e.args[0], errno.errorcode.get(e.args[0], '<no errno name>')))
					yield None  # stop the client connection
					break  # and don't come back

		yield None

	def writeData(self, data):
		return self.writer.send(data)


	def startData(self, command, data):
		# start the _write coroutine
		self.writer = self._write(self.sock)
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
			self.writer.send(header)  # write the response headers before the file

			self.writer.send(None)  # close the connection once the buffer is empty
		else:
			res = None

		# buffered, had_buffer
		return res

	def shutdown(self):
		try:
			self.sock.shutdown(socket.SHUT_RDWR)
		except socket.error:
			pass
		finally:
			self.sock.close()

		self.writer.close()
		self.reader.close()
