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

from exaproxy.icap.parser import ICAPParser

def ishex (s):
	return bool(s) and not bool(s.strip('0123456789abcdefABCDEF'))

def count_quotes (data):
	return data.count('"') - data.count('\\"')

class ICAPClient (object):
	eor = ['\r\n\r\n', '\n\n']

	__slots__ = ['name', 'ipv4', 'sock', 'peer', 'reader', 'writer', 'w_buffer', 'icap_parser', 'log']

	def __init__(self, name, sock, peer, logger, max_buffer):
		self.name = name
		self.ipv4 = isipv4(sock.getsockname()[0])
		self.sock = sock
		self.peer = peer
		self.reader = self._read(sock,max_buffer)
		self.writer = self._write(sock)
		self.w_buffer = ''

		self.icap_parser = ICAPParser(configuration={})
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
				return buff + eor, r_buffer[seek+pos+len(eor):], seek

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
		nb_to_send = 0
		content_length = 0
		seek = 0
		processing = False

		# mode can be one of : request, chunk, extension, relay
		# icap : we are reading the icap headers
		# request : we are reading the request (read all you can until a separator)
		# extra-headers : we are reading data until a separator
		# chunked : we are reading chunk-encoded darta
		# transfer : we are reading as much as requested in remaining
		# passthrough : read as much as can to be relayed

		mode = 'icap'

		while True:
			try:
				while True:
					if not processing:
						data = sock.recv(read_size)
						if not data:
							break  # read failed so we abort
						self.log.debug("<< [%s]" % data.replace('\t','\\t').replace('\r','\\r').replace('\n','\\n'))
						r_buffer += data
					else:
						processing = False

					if mode == 'passthrough':
						r_buffer, tmp = '', [r_buffer]
						yield [''], [''], tmp
						continue

					if nb_to_send:
						if mode == 'transfer' :
							r_len = len(r_buffer)
							length = min(r_len, nb_to_send)

							# do not yield yet if we are chunked since the end of the chunk may
							# very well be in the rest of the data we just read
							r_buffer, tmp = r_buffer[length:], [r_buffer[:length]]
							_, extra_size = yield [''], [''], tmp

							nb_to_send = nb_to_send - length + extra_size

							# we still have data to read before we can send more.
							if nb_to_send != 0:
								continue
							mode = 'icap'

						if mode == 'chunked':
							r_len = len(r_buffer)
							length = min(r_len, nb_to_send)

							# do not yield yet if we are chunked since the end of the chunk may
							# very well be in the rest of the data we just read
							if r_len <= nb_to_send:
								r_buffer, tmp = r_buffer[length:], [r_buffer[:length]]
								_, extra_size = yield '', '', tmp

								nb_to_send = nb_to_send - length + extra_size

								# we still have data to read before we can send more.
								if nb_to_send != 0:
									continue

					if mode == 'chunked':
						# sum of the sizes of all chunks in our buffer
						chunked, new_to_send = self.checkChunkSize(r_buffer[nb_to_send:])

						if new_to_send is None:
							# could not read any chunk (data is invalid)
							break

						nb_to_send += new_to_send
						if chunked:
							continue

						mode = 'end-chunk'

					# seek is only set if we already passed once and found we needed more data to check
					if mode == 'end-chunk':
						if r_buffer[nb_to_send:].startswith('\r\n'):
							nb_to_send += 2
							processing = True
							mode = 'transfer'
							continue
						elif r_buffer[nb_to_send:].startswith('\n'):
							nb_to_send += 1
							processing = True
							mode = 'transfer'
							continue

						if not r_buffer[nb_to_send:]:
							yield [''], [''], ['']
							continue

						mode = 'extra-headers'
						seek = nb_to_send

					if mode == 'extra-headers':
						# seek is up to where we know there is no double CRLF
						related, r_buffer, seek = self.checkRequest(r_buffer,max_buffer,seek)

						if related is None:
							# most likely could not find an header
							break

						if related:
							related, tmp = '', [related]
							yield [''], [''], tmp

						else:
							yield [''], [''], ['']
							continue

						seek = 0
						mode = 'transfer'

					if mode not in ('icap', 'request'):
						self.log.error('The programmers are monkeys - please give them bananas ..')
						self.log.error('the mode was spelled : [%s]' % mode)
						self.log.error('.. if it works, we are lucky - but it may work.')
						mode = 'icap'


					if mode == 'icap':
						# ignore EOL
						r_buffer = r_buffer.lstrip('\r\n')

						# check to see if we have read an entire request
						request, r_buffer, seek = self.checkRequest(r_buffer, max_buffer, seek)

						if request is None:
							# most likely could not find a header
							break

						if request:
							icap_request = request

							parsed_request = self.icap_parser.parseRequest(icap_request, '')
							content_length = parsed_request.content_length

							if parsed_request is None or parsed_request.contains_body:
								# we do not (yet) support having content sent to us
								break

							if not parsed_request.contains_headers:
								# we need at least an HTTP header
								break

							# no reason to keep this around in memory longer than we need it
							parsed_request = None

							request, seek = '', 0
							mode = 'request'

						else:
							yield [''], [''], ['']
							continue

					if mode == 'request':
						r_len = len(r_buffer)

						if r_len < content_length:
							yield [''], [''], ['']
							continue

					request, r_buffer = r_buffer[:content_length], r_buffer[content_length:]

					seek = 0
					processing = True

					# nb_to_send is how much we expect to need to get the rest of the request
					icap_request, tmp_icap = '', [icap_request]
					request, tmp = '', [request]

					mode, nb_to_send = yield tmp_icap, tmp, ['']

				# break out of the outer loop as soon as we leave the inner loop
				# through normal execution
				break

			except socket.error, e:
				if e.args[0] in errno_block:
					yield [''], [''], ['']
				else:
					break

		yield [None], [None], [None]


	def setPeer (self, peer):
		"""Set the claimed ip address for this client.
		Does not effect the ip address we try sending data to."""
		self.peer = peer

	def readData(self):
		# pop data from lists to free memory held by the coroutine
		icap_header_l, http_header_l, content_l = self.reader.send(('transfer',0))
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
							break      # terminate the client connection
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

	def restartData(self, command, data):
		self.writer = self._write(self.sock)
		return self.startData(command, data)

	def shutdown(self):
		try:
			self.sock.shutdown(socket.SHUT_RDWR)
		except socket.error:
			pass
		finally:
			self.sock.close()

		self.writer.close()
		self.reader.close()
