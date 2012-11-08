# encoding: utf-8
"""
downloader.py

Created by Thomas Mangin on 2011-12-01.
Copyright (c) 2011 Exa Networks. All rights reserved.
"""

import os

from exaproxy.util.log.logger import Logger
from exaproxy.http.response import http, file_header
from .worker import Content

class ParsingError (Exception):
	pass

class ContentManager(object):
	downloader_factory = Content

	def __init__(self, poller, location, page, configuration):
		self.total_sent = 0L
		self.opening = {}
		self.established = {}
		self.byclientid = {}
		self.buffered = []
		self.retry = []

		self.poller = poller
		self.log = Logger('download', configuration.log.download)

		self.location = os.path.realpath(os.path.normpath(location))
		self.page = page
		self._header = {}

	def hasClient(self, client_id):
		return client_id in self.byclientid

	def getLocalContent(self, code, name):
		filename = os.path.normpath(os.path.join(self.location, name))
		if not filename.startswith(self.location + os.path.sep):
			filename = ''

		if os.path.isfile(filename):
			try:
				stat = os.stat(filename)
			except IOError:
				content = 'close', http(501, 'local file is inaccessible %s' % str(filename))
			else:
				if filename in self._header :
					cache_time, header = self._header[filename]
				else:
					cache_time, header = None, None

				if cache_time is None or cache_time < stat.st_mtime:
					header = file_header(code, stat.st_size, filename)
					self._header[filename] = stat.st_size, header

				content = 'file', (header, filename)
		else:
			self.log.debug('local file is missing for %s: %s' % (str(name), str(filename)))
			content = 'close', http(501, 'could not serve missing file %s' % str(filename))

		return content

	def readLocalContent(self, code, reason, data={}):
		filename = os.path.normpath(os.path.join(self.location, reason))
		if not filename.startswith(self.location + os.path.sep):
			filename = ''

		if os.path.isfile(filename):
			try:
				with open(filename) as fd:
					body = fd.read() % data

				content = 'close', http(code, body)
			except IOError:
				self.log.debug('local file is missing for %s: %s' % (str(reason), str(filename)))
				content = 'close', http(501, 'could not serve missing file  %s' % str(reason))
		else:
			self.log.debug('local file is missing for %s: %s' % (str(reason), str(filename)))
			content = 'close', http(501, 'could not serve missing file  %s' % str(reason))

		return content


	def getDownloader(self, client_id, host, port, command, request):
		downloader = self.byclientid.get(client_id, None)
		if downloader:
			# XXX: A DNS redirector for part of a site could cause this test to fails
			# XXX: would it kill any download in progress for the client if it is a proxy ?
			if host != downloader.host or port != downloader.port:
				self.endClientDownload(client_id)
				downloader = None
			else:
				newdownloader = False

		if downloader is None:
			downloader = self.downloader_factory(client_id, host, port, command, request, self.log)
			newdownloader = True

		if downloader.sock is None:
			downloader = None
			newdownloader = False

		return downloader, newdownloader

	def getContent(self, client_id, command, args):
		try:
			if command == 'download':
				try:
					host, port, length, request = args.split('\0', 3)
				except (ValueError, TypeError), e:
					raise ParsingError()

				downloader, newdownloader = self.getDownloader(client_id, host, int(port), command, request)

				if downloader is not None:
					content = ('stream', '')
					length = int(length)
				else:
					content = self.getLocalContent('400', 'noconnect.html')
					length = 0

			elif command == 'connect':
				try:
					host, port, request = args.split('\0', 2)
				except (ValueError, TypeError), e:
					raise ParsingError()

				downloader, newdownloader = self.getDownloader(client_id, host, int(port), command, '')

				if downloader is not None:
					content = ('stream', '')
					length = -1 # the client can send as much data as it wants
				else:
					content = self.getLocalContent('400', 'noconnect.html')
					length = 0

			elif command == 'redirect':
				redirect_url = args
				headers = 'HTTP/1.1 302 Surfprotected\r\nCache-Control: no-store\r\nLocation: %s\r\n\r\n\r\n' % redirect_url

				downloader = None
				newdownloader = False
				request = ''
				content = ('close', headers)
				length = 0

			elif command == 'http':
				downloader = None
				newdownloader = False
				request = ''
				content = ('close', args)
				length = 0

			elif command == 'file':
				try:
					code, reason = args.split('\0', 1)
				except (ValueError, TypeError), e:
					raise ParsingError()

				downloader = None
				request = ''
				newdownloader = False
				content = self.getLocalContent(code, reason)
				length = 0

			elif command == 'rewrite':
				try:
					code, reason, comment, protocol, url, host, client_ip = args.split('\0', 6)
				except (ValueError, TypeError), e:
					raise ParsingError()

				downloader = None
				newdownloader = False
				request = ''
				content = self.readLocalContent(code, reason, {'url':url, 'host':host, 'client_ip':client_ip, 'protocol':protocol, 'comment':comment})
				length = 0

			elif command == 'monitor':
				path = args

				downloader = None
				newdownloader = False
				request = ''
				content = ('close', http('200', self.page.html(path)))
				length = 0

			else:
				downloader = None
				newdownloader = False
				request = ''
				content = None
				length = 0

		except ParsingError:
			self.log.error('problem getting content %s %s' % (type(e),str(e)))
			downloader = None
			newdownloader = False
			request = ''
			content = None
			length = 0

		if newdownloader is True:
			self.opening[downloader.sock] = downloader
			self.byclientid[downloader.client_id] = downloader

			buffered = None
			buffer_change = None

			# register interest in the socket becoming available
			self.poller.addWriteSocket('opening_download', downloader.sock)

		elif downloader is not None:
			buffered,sent = downloader.writeData(request)
			self.total_sent += sent
			if buffered:
				if downloader.sock not in self.buffered:
					self.buffered.append(downloader.sock)
					buffer_change = True
					# watch for the socket's send buffer becoming less than full
					self.poller.addWriteSocket('write_download', downloader.sock)
				else:
					buffer_change = False
			elif downloader.sock in self.buffered:
				self.buffered.remove(downloader.sock)
				buffer_change = True

				# we no longer care that we can write to the server
				self.poller.removeWriteSocket('write_download', downloader.sock)
			else:
				buffer_change = False
				
		elif client_id in self.byclientid:
			buffered = None
			buffer_change = None

			# we have replaced the downloader with local content
			self.endClientDownload(client_id)

		else:
			buffered = None
			buffer_change = None

		return content, length, buffered, buffer_change


	def startDownload(self, sock):
		# shift the downloader to the other connected sockets
		downloader = self.opening.pop(sock, None)
		if downloader:
			self.poller.removeWriteSocket('write_download', downloader.sock)

			self.established[sock] = downloader
			client_id, res, response = downloader.startConversation()

			# check to see if we were unable to connect
			if res is not True:
				_,response = self.readLocalContent('400', 'noconnect.html')

			# we're no longer interested in the socket connecting since it's connected
			self.poller.removeWriteSocket('opening_download', downloader.sock)

			# registed interest in data becoming available to read
			self.poller.addReadSocket('read_download', downloader.sock)

			if downloader.sock in self.buffered:
				# watch for the socket's send buffer becoming less than full
				self.poller.addWriteSocket('write_download', downloader.sock)

			buffer_change = downloader.sock in self.buffered

		else:
			client_id, response, buffer_change = None, None, None

		return client_id, response, buffer_change

	def retryDownload(self, client_id, command, args):
		return None

	def readData(self, sock):
		downloader = self.established.get(sock, None)
		if downloader:
			client_id = downloader.client_id
			data = downloader.readData()

			if data is None:
				self._terminate(sock, client_id)
		else:
			client_id, data = None, None

		return client_id, data

	def sendSocketData(self, sock, data):
		downloader = self.established.get(sock, None)
		if downloader:
			buffered,sent = downloader.writeData(data)
			self.total_sent += sent
			client_id = downloader.client_id

			if buffered:
				if sock not in self.buffered:
					self.buffered.append(sock)
					buffer_change = True

					# watch for the socket's send buffer becoming less than full
					self.poller.addWriteSocket('write_download', sock)
				else:
					buffer_change = False

			elif sock in self.buffered:
				self.buffered.remove(sock)
				buffer_change = True

				# we no longer care that we can write to the server
				self.poller.removeWriteSocket('write_download', sock)
			else:
				buffer_change = False

		else:
			buffered = None
			buffer_change = None
			client_id = None

		return buffered, buffer_change, client_id

	def sendClientData(self, client_id, data):
		downloader = self.byclientid.get(client_id, None)
		if downloader:
			if downloader.sock in self.established:
				buffered,sent = downloader.writeData(data)
				self.total_sent += sent

				if buffered:
					if downloader.sock not in self.buffered:
						self.buffered.append(downloader.sock)
						buffer_change = True

						# watch for the socket's send buffer becoming less than full
						self.poller.addWriteSocket('write_download', downloader.sock)
					else:
						buffer_change = True

				elif downloader.sock in self.buffered:
					self.buffered.remove(downloader.sock)
					buffer_change = True

					# we no longer care that we can write to the server
					self.poller.removeWriteSocket('write_download', downloader.sock)
				else:
					buffer_change = False


			elif downloader.sock in self.opening:
				buffered = downloader.bufferData(data)
				if downloader.sock not in self.buffered:
					self.buffered.append(downloader.sock)
					buffer_change = True

				else:
					buffer_change = False


			else:  # what is going on if we reach this point
				self._terminate(downloader.sock, client_id)
				buffered = None
				buffer_change = None
		else:
			buffered = None
			buffer_change = None

		return buffered, buffer_change


	def endClientDownload(self, client_id):
		downloader = self.byclientid.get(client_id, None)
		if downloader:
			res = self._terminate(downloader.sock, client_id)
		else:
			res = False

		return res

	def corkClientDownload(self, client_id):
		downloader = self.byclientid.get(client_id, None)
		if downloader:
			self.poller.corkReadSocket('read_download', downloader.sock)

	def uncorkClientDownload(self, client_id):
		downloader = self.byclientid.get(client_id, None)
		if downloader:
			if downloader.sock in self.established:
				self.poller.uncorkReadSocket('read_download', downloader.sock)

	def _terminate(self, sock, client_id):
		downloader = self.established.get(sock, None)
		if downloader is None:
			downloader = self.opening.get(sock, None)

			if downloader:
				# we no longer care about the socket connecting
				self.poller.removeWriteSocket('opening_download', downloader.sock)
		else:
			# we no longer care about the socket being readable
			self.poller.removeReadSocket('read_download', downloader.sock)

		if downloader:
			self.established.pop(sock, None)
			self.opening.pop(sock, None)
			self.byclientid.pop(client_id, None)

			if sock in self.buffered:
				self.buffered.remove(sock)

				# we no longer care about the socket's send buffer becoming less than full
				self.poller.removeWriteSocket('write_download', downloader.sock)

			downloader.shutdown()

			res = True
		else:
			res = False

		return res


	def stop (self):
		opening = self.opening.itervalues()
		established = self.established.itervalues()

		for gen in (opening, established):
			for downloader in gen:
				downloader.shutdown()

		self.established = {}
		self.opening = {}
		self.byclientid = {}
		self.buffered = []

		self.poller.clearRead('read_download')
		self.poller.clearWrite('write_download')
		self.poller.clearWrite('opening_download')

		return True

