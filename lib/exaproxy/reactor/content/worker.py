# encoding: utf-8
"""
worker.py

Created by Thomas Mangin on 2011-12-01.
Copyright (c) 2011-2013  Exa Networks. All rights reserved.
"""

from exaproxy.network.functions import connect,isipv4
from exaproxy.network.errno_list import errno_block
from exaproxy.network.errno_list import errno_unavailable

import socket
import errno

# http://tools.ietf.org/html/rfc2616#section-8.2.3
# Says we SHOULD keep track of the server version and deal with 100-continue
# I say I am too lazy - and if you want the feature use this software as as rev-proxy :D

DEFAULT_READ_BUFFER_SIZE = 64*1024


class Content (object):
	_connect = staticmethod(connect)

	__slots__ = ['client_id', 'sock', 'host', 'port', 'method', 'w_buffer', 'log', 'ipv4']

	def __init__(self, client_id, host, port, bind, method, request, logger):
		self.client_id = client_id
		self.sock = self._connect(host, port, bind)
		self.host = host
		self.port = port
		self.method = method
		self.w_buffer = request
		self.log = logger
		self.ipv4 = isipv4(host)

	def startConversation(self):
		"""Send our buffered request to get the conversation flowing
		Don't send anything yet if the client sent a CONNECT - instead,
		we respond with our own HTTP header indicating that we connected"""

		#self.log.info('download socket is now open for client %s %s' % (self.client_id, self.sock))

		res,sent4,sent6 = self.writeData('')
		# XXX: Are we not accounting this data transfer ! ?
		response='HTTP/1.1 200 Connection Established\r\n\r\n' if self.method == 'connect' else ''
		return self.client_id, res is not None, response

	def readData(self, buflen=DEFAULT_READ_BUFFER_SIZE):
		"""Read data that we have already received from the remote server"""

		try:
			# without this the exception can barf with data not defined on error
			data = ''
			data = self.sock.recv(buflen) or None
			#if data:
			#	self.log.debug("<< [%s]" % data.replace('\t','\\t').replace('\r','\\r').replace('\n','\\n'))
		except socket.error, e:
			if e.args[0] in errno_block:
				self.log.info('interrupted when trying to read, will retry: got %s bytes' % len(data))
				self.log.info('reason, errno %d: %s' % (e.args[0], errno.errorcode.get(e.args[0], '<no errno name>')))
				data = ''
			else:
				#self.log.info('unexpected error reading on socket')
				#self.log.info('reason, errno %d: %s' % (e.args[0], errno.errorcode.get(e.args[0], '<no errno name>')))
				data = None

		return data

	def writeData(self, data):
		"""Write data to the remote server"""

		w_buffer = self.w_buffer + data

		try:
			sent = self.sock.send(w_buffer)
			#if sent:
			#	self.log.debug(">> [%s]" % w_buffer[:sent].replace('\t','\\t').replace('\r','\\r').replace('\n','\\n'))
			#self.log.info('sent %s of %s bytes of data. %s bytes were unbuffered : %s' % (sent, len(w_buffer), len(data), self.sock))
			self.w_buffer = w_buffer[sent:]
			res = bool(self.w_buffer)

		except socket.error, e:
			sent = 0
			self.w_buffer = w_buffer

			if e.args[0] in errno_block:
				#self.log.error('Write failed as it would have blocked. Why were we woken up? Error %d: %s' % (e.args[0], errno.errorcode.get(e.args[0], '')))
				res = bool(self.w_buffer)
			elif e.args[0] in errno_unavailable:
				res = None
			else:
				res = None

		return res,sent if self.ipv4 else 0, 0 if self.ipv4 else sent

	def bufferData(self, data):
		"""Buffer data to be sent later"""
		self.w_buffer += data
		return bool(self.w_buffer)

	def shutdown(self):
		try:
			self.sock.shutdown(socket.SHUT_RDWR)
		except socket.error:
			pass
		finally:
			self.sock.close()
