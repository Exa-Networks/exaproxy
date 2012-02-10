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
from exaproxy.http.response import http, file_header
from exaproxy.content.downloader import Downloader

import os
import socket
import errno

class ParsingError (Exception):
	pass

class ContentManager(object):
	downloader_factory = Downloader

	def __init__(self, poller, location, page):
		self.total_sent = 0L
		self.opening = {}
		self.established = {}
		self.byclientid = {}
		self.buffered = []
		self.retry = []

		self.poller = poller

		self.location = location
		self.page = page
		self._header = {}

	def getLocalContent(self, code, name):
		filename = os.path.normpath(os.path.join(self.location, name))
		if not filename.startswith(self.location + os.path.sep):
			filename = ''

		if os.path.isfile(filename):
			try:
				stat = os.stat(filename)
			except IOError:
				content = 'close', http(501, 'unable to stat file: %s' % str(filename))
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
			logger.debug('download', 'no file exists for %s: %s' % (str(name), str(filename)))
			content = 'close', http(501, 'no file exists for %s: %s' % (str(name), str(filename)))

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
				logger.debug('download', 'no file exists for %s: %s' % (str(reason), str(filename)))
				content = 'close', http(501, 'no file exists for %s' % str(reason))
		else:
			logger.debug('download', 'no file exists for %s: %s' % (str(reason), str(filename)))
			content = 'close', http(501, 'no file exists for %s' % str(reason))
			
		return content


	def newDownloader(self, client_id, host, port, command, request):
		downloader = self.downloader_factory(client_id, host, port, command, request)
		if downloader.sock is None:
			downloader = None

		return downloader

	def getContent(self, client_id, decision):
		try:
			try:
				command, args = decision.split('\0', 1)
			except (ValueError, TypeError), e:
				raise ParsingError()

			if command == 'download':
				try:
					host, port, request = args.split('\0', 2)
				except (ValueError, TypeError), e:
					raise ParsingError()

				downloader = self.newDownloader(client_id, host, int(port), command, request)
				content = ('stream', '') if downloader is not None else None
				restricted = True

			elif command == 'connect':
				try:
					host, port, request = args.split('\0', 2)
				except (ValueError, TypeError), e:
					raise ParsingError()

				downloader = self.newDownloader(client_id, host, int(port), command, '')
				content = ('stream', '') if downloader is not None else None
				restricted = False

			elif command == 'redirect':
				redirect_url = args
				headers = 'HTTP/1.1 302 Surfprotected\r\nLocation: %s\r\n\r\n\r\n' % redirect_url

				downloader = None
				content = ('close', headers)
				restricted = True

			elif command == 'html':
				try:
					code, data = args.split('\0', 1)
				except (ValueError, TypeError), e:
					raise ParsingError()

				downloader = None
				content = ('close', http(code, data))
				restricted = True

			elif command == 'file':
				try:
					code, reason = args.split('\0', 1)
				except (ValueError, TypeError), e:
					raise ParsingError()

				downloader = None
				content = self.getLocalContent(code, reason)
				restricted = True

			elif command == 'rewrite':
				try:
					code, reason, protocol, url, host, client_ip = args.split('\0', 5)
				except (ValueError, TypeError), e:
					raise ParsingError()

				downloader = None
				content = self.readLocalContent(code, reason, {'url':url, 'host':host, 'client_ip':client_ip, 'protocol':protocol})
				restricted = True

			elif command == 'monitor':
				path = args

				downloader = None
				content = ('close', http('200', self.page.html(path)))
				restricted = True

			else:
				downloader = None
				content = None
				restricted = None

		except ParsingError:
			logger.error('download', 'problem getting content %s %s' % (type(e),str(e)))
			downloader = None
			content = None
			restricted = None

		if downloader is not None:
			self.opening[downloader.sock] = downloader
			self.byclientid[downloader.client_id] = downloader

			# register interest in the socket becoming available
			self.poller.addWriteSocket('opening_download', downloader.sock)

		return content, restricted


	def startDownload(self, sock):
		# shift the downloader to the other connected sockets
		downloader = self.opening.pop(sock, None)
		if downloader:
			self.poller.removeWriteSocket('write_download', downloader.sock)

			self.established[sock] = downloader
			client_id, response = downloader.startConversation()

			# we're no longer interested in the socket connecting since it's connected
			self.poller.removeWriteSocket('opening_download', downloader.sock)

			# registed interest in data becoming available to read
			self.poller.addReadSocket('read_download', downloader.sock)

			flipflop = downloader.sock in self.buffered

		else:
			client_id, response, flipflop = None, None, None

		return client_id, response, flipflop

	def retryDownload(self, client_id, decision):
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
			had_buffer = True if downloader.w_buffer else False
			buffered,sent = downloader.writeData(data)
			self.total_sent += sent

			if buffered:
				if sock not in self.buffered:
					self.buffered.append(sock)
					flipflop = True
	
					# watch for the socket's send buffer becoming less than full
					self.poller.addWriteSocket('write_download', sock)
				else:
					flipflop = False

			elif had_buffer and sock in self.buffered:
				self.buffered.remove(sock)
				flipflop = True

				# we no longer care that we can write to the server
				self.poller.removeWriteSocket('write_download', sock)
			else:
				flipflop = False

		else:
			buffered = None
			flipflop = None

                return buffered, flipflop

	def sendClientData(self, client_id, data):
		downloader = self.byclientid.get(client_id, None)
		if downloader:
			if downloader.sock in self.established:
				had_buffer = True if downloader.w_buffer else False
				buffered,sent = downloader.writeData(data)
				self.total_sent += sent
			
				if buffered:
					if downloader.sock not in self.buffered:
						self.buffered.append(downloader.sock)
						flipflop = True

						# watch for the socket's send buffer becoming less than full
						self.poller.addWriteSocket('write_download', downloader.sock)
					else:
						flipflop = False

				elif had_buffer and sock in self.buffered:
					self.buffered.remove(sock)
					flipflop = True

					# we no longer care that we can write to the server
					self.poller.removeWriteSocket('write_download', downloader.sock)
				else:
					flipflop = False


			elif downloader.sock in self.opening:
				buffered = downloader.bufferData(data)
				if downloader.sock not in self.buffered:
					self.buffered.append(downloader.sock)
					flipflop = True

					# watch for the socket's send buffer becoming less than full
					self.poller.addWriteSocket('write_download', downloader.sock)
				else:
					flipflop = False
	

			else:  # what is going on if we reach this point
				self._terminate(downloader.sock, client_id)
				buffered = None
				flipflop = None
		else:
			buffered = None
			flipflop = None

		return buffered, flipflop


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

