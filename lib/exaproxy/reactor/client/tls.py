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

from exaproxy.tls.decode import get_tls_hello_size
from exaproxy.tls.header import TLS_HEADER_LEN

from exaproxy.util.proxy import ProxyProtocol


class TLSClient (object):
	eor = ['\r\n\r\n', '\n\n']
	eol = ['\r\n', '\n']
	proxy_protocol = ProxyProtocol()

	__slots__ = ['name', 'ipv4', 'sock', 'accept_addr', 'accept_port', 'peer', 'reader', 'writer', 'w_buffer', 'log']

	def __init__(self, name, sock, peer, logger, max_buffer, proxied):
		addr, port = sock.getsockname()
		self.name = name
		self.sock = sock
		self.peer = peer
		self.accept_addr = addr
		self.accept_port = port
		self.ipv4 = isipv4(addr)
		self.reader = self._read(sock, max_buffer, proxied=proxied)
		self.writer = self._write(sock)
		self.w_buffer = ''

		self.log = logger

		# start the _read coroutine
		self.reader.next()

	def checkRequest (self, r_buffer, max_length, size=None):
		if size == 0 and len(r_buffer) < TLS_HEADER_LEN:
			return '', r_buffer, None

		if size == 0:
			size = get_tls_hello_size(r_buffer)

		if size <= 0 or size > max_length:
			return None, None, None

		if len(r_buffer) >= size:
			return r_buffer[:size], r_buffer[size:], size

		return '', r_buffer, size


	def _read (self, sock, max_buffer, read_size=64*1024, proxied=False):
		"""Coroutine managing data read from the client"""
		# yield request, content
		# request is the text that form the request header
		# content any text which is related to the current request after the headers

		yield ''

		r_buffer = ''
		size = 0
		masquerade = None

		# mode can be one of : request, chunk, extension, relay
		# proxy: we are reading an opening proxy protocol header
		# tls : we are reading the header
		# passthrough : read as much as can to be relayed

		mode = 'proxy' if proxied else 'tls'
		tls_header = ''
		data = ''

		while True:
			try:
				while True:
					if mode != 'passthrough' or r_buffer == '':
						new_data = sock.recv(read_size)
						if not new_data:
							break # read failed so we abort

						r_buffer += new_data

					if mode == 'proxy':
						masquerade, r_buffer, mode = self.processProxyHeader(r_buffer, mode)
						if masquerade is None:
							break

						elif not masquerade:
							continue

						self.setPeer(masquerade)

					# check for a new tls header
					if mode == 'tls':
						tls_header, r_buffer, size = self.checkRequest(r_buffer, max_buffer, size)
						if tls_header is None:
							break

					# all modes that are not directly related to reading a new header
					if mode != 'tls':
						data, r_buffer, mode = self.process(r_buffer, mode, max_buffer)
						if data is None:
							break

					# return header or data stream
					if mode == 'tls' and tls_header:
						tls_response, tls_header = [tls_header], ''
						size = 0

						mode, _ = yield tls_response, ['']

					elif data:
						data_response, data = [data], ''
						yield [''], data_response

					else:
						yield [''], ['']


				# break out of the outer loop as soon as we leave the inner loop
				# through normal execution
				break

			except socket.error, e:
				if e.args[0] in errno_block:
					yield [''], ['']
				else:
					break

		yield [None], [None]


	def processProxyHeader (self, r_buffer, mode):
		r_buffer = r_buffer.lstrip('\r\n')

		for eol in self.eol:
			if eol in r_buffer:
				client_ip, r_buffer = self.proxy_protocol.parse(r_buffer)
				mode = 'tls'
				break

			else:
				client_ip, r_buffer = '', r_buffer

		return client_ip, r_buffer, mode

	def process (self, r_buffer, mode, max_buffer):
		if mode == 'passthrough':
			data, r_buffer, new_mode = r_buffer, '', mode

		else:
			data, r_buffer, new_mode = None, r_buffer, None

		return data, r_buffer, new_mode


	def setPeer (self, peer):
		"""Set the claimed ip address for this client.
		Does not effect the ip address we try sending data to."""
		self.peer = peer

	def readData (self):
		# pop data from lists to free memory held by the coroutine
		request_l, content_l = self.reader.send(('new-request',0))
		request = request_l.pop()
		content = content_l.pop()

		return self.name, self.accept_addr, self.peer, request, '', content

	def readRelated (self, mode, remaining):
		# pop data from lists to free memory held by the coroutine
		mode = mode or 'new-request'
		request_l, content_l = self.reader.send((mode,remaining))
		request = request_l.pop()
		content = content_l.pop()

		return self.name, self.accept_addr, self.peer, request, '', content

	def _write(self, sock):
		"""Coroutine managing data sent to the client"""

		data = yield None
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
			res = self.writer.send(data)

		elif command == 'close':
			self.writer.send(data)
			res = self.writer.send(None)  # close the connection once the buffer is empty

		else:
			res = None

		# buffered, had_buffer
		return self.name, self.peer, res

	def shutdown(self):
		try:
			self.sock.shutdown(socket.SHUT_RDWR)
		except socket.error:
			pass
		finally:
			self.sock.close()

		self.writer.close()
		self.reader.close()
