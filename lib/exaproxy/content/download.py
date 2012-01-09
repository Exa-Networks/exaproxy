#!/usr/bin/env python
# encoding: utf-8
"""
downloader.py

Created by Thomas Mangin on 2011-12-01.
Copyright (c) 2011 Exa Networks. All rights reserved.
"""

from exaproxy.util.logger import logger
from exaproxy.nettools import connected_tcp_socket

import socket

# http://tools.ietf.org/html/rfc2616#section-8.2.3
# Says we SHOULD keep track of the server version and deal with 100-continue
# I say I am too lazy - and if you want the feature use this software as as rev-proxy :D


DEFAULT_READ_BUFFER_SIZE = 4096


class DownloadManager(object):
	def __init__(self, location):
		self.download = Download()
		self.location = location
		self.retry = []

		# XXX: clean this up
		self.established = self.download.connections
		self.opening = self.download.connecting
		self.byclientid = self.download.byclientid

	def getLocalContent(self, name):
		filename = os.path.join(self.location, name)
		if os.path.isfile(filename):
			content = 'local', filename
		else: 
			logger.debug('download', 'no file exists for %s: %s' % (str(name), str(filename)))
			content = None

		return content


	def getContent(self, client_id, decision):
		try:
			command, args = decision.split('\0', 1)

			if command in ('download', 'connect'):
				host, port, request = args.split('\0', 2)
				print '='*60
				print request.replace('\0', '\r\n')
				print '='*60


				result = self.download.newConnection(client_id, host, int(port), request.replace('\0', '\r\n'))
				print "++++++++++++++++ NEW CONNETION RESULT IS", result
				content = ('stream', '') if result is True else None

			elif command == 'data':
				code, data = args.split('\0', 1)
				content = ('stream', data.replace('\0', '\r\n'))

			elif command == 'local':
				code, reason = args.split('\0', 1)
				content = self.getLocalContent(reason)

		except (ValueError, TypeError), e:
			print "******** PROBLEM GETTING CONTENT"
			print "********", type(e),str(e)
			# XXX: log 
			content = None

		return content

	def startDownload(self, sock):
		return self.download.start(sock)

	def retryDownload(self, client_id, decision):
		return None

        def readData(self, sock, bufsize=0):
		return self.download.readData(sock, bufsize)

        def endClientDownload(self, client_id):
		return self.download.endClientDownload(client_id)



class Download(object):
	socket = staticmethod(connected_tcp_socket)

	def __init__(self):
		self.connections = {}
		self.connecting = {}
		self.byclientid = {}

	def _download(self, sock, request, default_buffer_size=DEFAULT_READ_BUFFER_SIZE):
		"""Coroutine that manages our connection to the remote server"""

		# We're already connected so send the request immediately
		sent = sock.send(request)
		bufsize = yield sent	# XXX: could block if the request is large

		# if the end user connection dies before we finished downloading for it
		# then we send None to signal this coroutine to give up 
		while bufsize is not None:
			r_buffer = sock.recv(bufsize or default_buffer_size)
			if not r_buffer:
				break

			bufsize = yield r_buffer

		# XXX: should we indicate whether we downloaded the entire file
		# XXX: or encountered an error

		# signal that there is nothing more to download
		yield None

	def newConnection(self, client_id, host, port, request):
		sock = self.socket(host, port)

		# sock will be None if there was a temporary error
		if sock is not None:
			self.connecting[sock] = client_id, request

		print "+++++++ GOT SOCKET ", sock
		return True if sock is not None else None

	def start(self, sock):
		# the socket is now open
		res = self.connecting.pop(sock, None)
		if res is not None:
			client_id, request = res
			fetcher = self._download(sock, request)
			fetcher.next() # immediately send the request

			self.connections[sock] = fetcher, client_id
			self.byclientid[client_id] = fetcher, sock
			result = True
		else:
			result = False

		return False

	def _terminate(self, sock):
		sock.shutdown(socket.SHUT_RDWR)
		fetcher, client_id = self.connections.pop(sock, None)
		# XXX: log something if we did not have the client_id in self.byclientid
		if client_id is not None:
			self.byclientid.pop(client_id, None)

		return fetcher is not None

	# XXX: track the total number of bytes read in the content
	# XXX: (not including headers)
	def readData(self, sock, bufsize=0):
		fetcher, client_id = self.connections.get(sock, None)
		if fetcher is not None:
			data = fetcher.send(bufsize)
		else:
			data = None

		if fetcher and data is None:
			self._terminate(sock)

		return client_id, data

	def endClientDownload(self, client_id):
		fetcher, sock = self.byclientid.get(client_id, (None, None))
		if fetcher is not None:
			res = fetcher.send(None)
			response = res is None

			# XXX: written in a hurry - check this is right
			self.connections.pop(sock, None)
			self.byclientid.pop(client_id, None)
		else:
			response = None

		return response

	def cleanup(self, sock):
		res = self.connecting.pop(sock, None)
		return res is not None
