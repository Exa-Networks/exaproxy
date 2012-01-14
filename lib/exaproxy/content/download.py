#!/usr/bin/env python
# encoding: utf-8
"""
downloader.py

Created by Thomas Mangin on 2011-12-01.
Copyright (c) 2011 Exa Networks. All rights reserved.
"""

from exaproxy.util.logger import logger
from exaproxy.nettools import connected_tcp_socket
from exaproxy.http.response import http

import os
import socket
import errno

# http://tools.ietf.org/html/rfc2616#section-8.2.3
# Says we SHOULD keep track of the server version and deal with 100-continue
# I say I am too lazy - and if you want the feature use this software as as rev-proxy :D

BLOCKING_ERRORS = (errno.EAGAIN,errno.EINTR,errno.EWOULDBLOCK,errno.EINTR)

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
		self.buffered = self.download.buffered

	def getLocalContent(self, name):
		if not name.startswith('/'):
			filename = os.path.join(self.location, name)
		else:
			filename = name
		if os.path.isfile(filename):
			content = 'local', filename
		else: 
			logger.debug('download', 'no file exists for %s: %s' % (str(name), str(filename)))
			content = None

		return content


	def getContent(self, client_id, decision):
		try:
			command, args = decision.split('\0', 1)

			if command in ('download'):
				host, port, request = args.split('\0', 2)

				result = self.download.newConnection(client_id, host, int(port), request.replace('\0', '\r\n'))
				content = ('stream', '') if result is True else None

			elif command == 'connect':
				host, port, response = args.split('\0', 2)

				result = self.download.newConnection(client_id, host, int(port), None)
				content = ('stream', '') if result is True else None

			elif command == 'html':
				code, data = args.split('\0', 1)
				content = ('html', http(code,data.replace('\0', os.linesep)))

			elif command == 'file':
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

	def sendClientData(self, client_id, data):
		return self.download.sendClientData(client_id, data)

	def sendSocketData(self, socket, data):
		return self.download.sendSocketData(socket, data)

	def stop (self):
		# XXX: Fixme
		print "STOP exists to not cause close warning"
		pass

class Download(object):
	socket = staticmethod(connected_tcp_socket)

	def __init__(self):
		self.connections = {}
		self.connecting = {}
		self.byclientid = {}
		self.buffered = []


	def _read(self, sock, default_buffer_size=DEFAULT_READ_BUFFER_SIZE):
		"""Coroutine that reads data from our connection to the remote server"""

		bufsize = yield '' # start the coroutine

		while True:     # Enter the exception handler as infrequently as possible
			try:
				# If the end user connection dies before we finished downloading from it
				# then we send None to signal this coroutine to give up
				while bufsize is not None:
					r_buffer = sock.recv(bufsize or default_buffer_size)
					if not r_buffer:
						break

					bufsize = yield r_buffer

				break # exit the outer loop

			except socket.error, e:
				if e.errno in BLOCKING_ERRORS:
					logger.error('download', 'Write failed as it would have blocked. Why were we woken up? Error %d: %s' % (e.errno, errno.errorcode.get(e.errno, '')))
					yield ''
				else:
					print "????? ARRGH - BAD DOWNLOADER ?????", type(e), str(e)
					break # stop downloading

		# XXX: should we indicate whether we downloaded the entire file
		# XXX: or encountered an error

		r_buffer = None
		# signal that there is nothing more to download
		yield None
				

	def _write(self, sock):
		"""Coroutine that manages data to be sent to the remote server"""

		# XXX:
		# TODO: use a file for buffering data rather than storing
		#       it in memory

		data = yield None # start the coroutine
		print "DOWNLOAD WRITER STARTED WITH %s BYTES: %s" % (len(data) if data is not None else None, sock)
		w_buffer = ''

		while True: # enter the exception handler as infrequently as possible
			try:
				while True:
					had_buffer = True if w_buffer else False

					if data is not None:
						 w_buffer = (w_buffer + data) if data else w_buffer
					else:
						if had_buffer: # we'll be back
							yield None
						break

					if not had_buffer or not data:
						sent = sock.send(w_buffer)
						print "SENT %s of %s BYTES OF DATA: %s" % (sent, len(data), sock)
						w_buffer = w_buffer[sent:]

					data = yield (True if w_buffer else False), had_buffer

				break	# break out of the outer loop as soon as we leave the inner loop
					# through normal execution

			except socket.error, e:
				if e.errno in BLOCKING_ERRORS:
					logger.error('download', 'Write failed as it would have blocked. Why were we woken up? Error %d: %s' % (e.errno, errno.errorcode.get(e.errno, '')))
					data = yield (True if w_buffer else False), had_buffer
				else:
					break

		yield None # close the connection

	def newConnection(self, client_id, host, port, request):
		sock = self.socket(host, port)

		print "NEW DOWNLOAD SOCKET FOR CLIENT %s: %s" % (client_id, sock)

		# sock will be None if there was a temporary error
		if sock is not None:
			self.connecting[sock] = client_id, request

		return True if sock is not None else None

	def start(self, sock):
		# the socket is now open
		res = self.connecting.pop(sock, None)
		if res is not None:
			client_id, request = res
			print "DOWNLOAD SOCKET IS NOW OPEN FOR CLIENT %s: %s" % (client_id, sock)
			print "GOING TO SEND %s BYTE REQUEST FOR CLIENT %s: %s" % (len(request or ''), client_id, sock)
			fetcher = self._read(sock)
			fetcher.next()       # start the fetcher coroutine

			sender = self._write(sock)
			sender.next()        # start the sender coroutine

			# XXX: We MUST send method to newConnection rather than checking for a null request
			if request is not None:
				sender.send(request) # immediately send the request

			self.connections[sock] = fetcher, sender, client_id
			self.byclientid[client_id] = fetcher, sender, sock
			
			# XXX: We MUST send method to newConnection rather than checking for a null request
			response='HTTP/1.1 200 Connection Established\r\n\r\n' if request is None else ''
			result = client_id, response
		else:
			result = None, None

		return result


	def sendClientData(self, client_id, data):
		fetcher, sender, sock = self.byclientid.get(client_id, (None, None, None))
		if sock is None:
			logger.error('download', 'Fatal? Received data from a client we do not recognise: %s' % client_id)
			return None

		print "GOING TO SEND %s BYTES OF DATA FOR CLIENT %s: %s" % (len(data) if data is not None else None, client_id, sock)
		res = sender.send(data)

		if res is None:
			if sock not in self.buffered:
				self._terminate(sock)
			else:
				print "SOCK WAS CLOSED BEFORE WE COULD EMPTY ITS BUFFER", sock
			return None

		buffered, had_buffer = res

		if buffered:
			if sock not in self.buffered:
				self.buffered.append(sock)
		elif had_buffer and sock in self.buffered:
			self.buffered.remove(sock)

		return True

	def sendSocketData(self, sock, data):
		fetcher, sender, client_id = self.connections.get(sock, (None, None, None))
		if client_id is None:
			logger.error('download', 'Fatal? Sending data on a socket we do not recognise: %s' % sock)
			print len(self.connections), sock in self.connections
			return None


		print "FLUSHING DATA WITH %s BYTES FOR CLIENT %s: %s" % (len(data) if data is not None else None, client_id, sock)

		res = sender.send(data)

		if res is None:
			if sock in self.buffered:
				self.buffered.remove(sock)
			print "SEND SOCKET DATA - TERMINATING BECAUSE WE COULD NOT SEND DATA", sock
			self._terminate(sock) # XXX: should return None - check that 'fixing' _terminate doesn't break anything
			return None

		buffered, had_buffer = res

		if buffered:
			if sock not in self.buffered:
				self.buffered.append(sock)
		elif had_buffer and sock in self.buffered:
			self.buffered.remove(sock)

		return True


	def _terminate(self, sock):
		try:
			sock.shutdown(socket.SHUT_RDWR)
			sock.close()
		except socket.error:
			pass

		fetcher, sender, client_id = self.connections.pop(sock, None)
		print 'CLOSING DOWNLOAD SOCKET USED BY CLIENT %s: %s'  % (client_id, sock)
		# XXX: log something if we did not have the client_id in self.byclientid
		if client_id is not None:
			self.byclientid.pop(client_id, None)

		if sock in self.buffered:
			self.buffered.remove(sock)

		return fetcher is not None

	# XXX: track the total number of bytes read in the content
	# XXX: (not including headers)
	def readData(self, sock, bufsize=0):
		fetcher, sender, client_id = self.connections.get(sock, (None, None, None))
		if client_id is None:
			logger.error('download', 'Fatal? Trying to read data on a socket we do not recognise: %s' % sock)

		if fetcher is not None:
			data = fetcher.send(bufsize)
		else:
			print "NO FETCHER FOR", sock
			data = None


		print "DOWNLOADED %s BYTES OF DATA FOR CLIENT %s: %s" % (len(data) if data is not None else None, client_id, sock)

		if fetcher and data is None:
			self._terminate(sock)
		elif data is None:
			print "NOT TERMINATING BECAUSE THERE IS NO FETCHER"

		return client_id, data

	def endClientDownload(self, client_id):
		fetcher, sender, sock = self.byclientid.get(client_id, (None, None, None))
		print "ENDING DOWNLOAD FOR CLIENT %s: %s" % (client_id, sock)
		if fetcher is not None:
			res = fetcher.send(None)
			response = res is None

			# XXX: written in a hurry - check this is right
			self._terminate(sock)
		else:
			response = None

		return response

	def cleanup(self, sock):
		res = self.connecting.pop(sock, None)
		return res is not None
