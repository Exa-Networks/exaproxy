#!/usr/bin/env python
# encoding: utf-8
"""
downloader.py

Created by Thomas Mangin on 2011-12-01.
Copyright (c) 2011 Exa Networks. All rights reserved.
"""

from exaproxy.util.logger import logger
from exaproxy.network.functions import connect
from exaproxy.network.poller import errno_block
from exaproxy.http.response import http

import os
import socket
import errno

# http://tools.ietf.org/html/rfc2616#section-8.2.3
# Says we SHOULD keep track of the server version and deal with 100-continue
# I say I am too lazy - and if you want the feature use this software as as rev-proxy :D

DEFAULT_READ_BUFFER_SIZE = 64*1024


class Downloader(object):
	_connect = staticmethod(connect)

	def __init__(self, client_id, host, port, method, request):
		self.client_id = client_id
		self.sock = self._connect(host, port)
		self.method = method
		self.w_buffer = request

	def startConversation(self):
		"""Send our buffered request to get the conversation flowing
		Don't send anything yet if the client sent a CONNECT - instead,
		we respond with our own HTTP header indicating that we connected"""

		logger.info('download', 'download socket is now open for client %s %s' % (self.client_id, self.sock))

		self.writeData('')
		response='HTTP/1.1 200 Connection Established\r\n\r\n' if self.method == 'connect' else ''
		return self.client_id, response
		
	def readData(self, buflen=DEFAULT_READ_BUFFER_SIZE):
		"""Read data that we have already received from the remote server"""

		try:
			data = self.sock.recv(buflen)
			if not data:
				data = None
		except socket.error, e:
			if e.errno in errno_block:
				logger.error('download','write failed as it would have blocked. Why were we woken up?')
				logger.error('download','Error %d: %s' % (e.errno, errno.errorcode.get(e.errno, '')))
				data = ''
			else:
				data = None

		return data

	def writeData(self, data):
		"""Write data to the remote server"""

		w_buffer = self.w_buffer + data

		try:
			sent = self.sock.send(w_buffer)
			logger.info('download', 'sent %s of %s bytes of data : %s' % (sent, len(data), self.sock))
			self.w_buffer = w_buffer[sent:]
			res = True if self.w_buffer else False
		except socket.error, e:
			if e.errno in errno_block:
				logger.error('download', 'Write failed as it would have blocked. Why were we woken up? Error %d: %s' % (e.errno, errno.errorcode.get(e.errno, '')))
				res = True if self.w_buffer else False
			else:
				res = None

		return res

	def bufferData(self, data):
		"""Buffer data to be sent later"""
		self.w_buffer += data
		return bool(self.w_buffer)

	def shutdown(self):
		try:
			self.sock.shutdown(socket.SHUT_RDWR)
			self.sock.close()
		except socket.error:
			pass

