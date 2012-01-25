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


class ContentManager(object):
	downloader_factory = Downloader

	def __init__(self, location):
		self.opening = {}
		self.established = {}
		self.byclientid = {}
		self.buffered = []
		self.retry = []

		self.location = location
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
			command, args = decision.split('\0', 1)

			if command == 'download':
				host, port, request = args.split('\0', 2)

				downloader = self.newDownloader(client_id, host, int(port), command, request)
				content = ('stream', '') if downloader is not None else None
				restricted = True

			elif command == 'connect':
				host, port, request = args.split('\0', 2)

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
				code, data = args.split('\0', 1)

				downloader = None
				content = ('close', http(code, html))
				restricted = True

			elif command == 'file':
				code, reason = args.split('\0', 1)
				downloader = None
				content = self.getLocalContent(code, reason)
				restricted = True

			elif command == 'rewrite':
				code, reason, protocol, url, host, client_ip = args.split('\0', 5)

				downloader = None
				content = self.readLocalContent(code, reason, {'url':url, 'host':host, 'client_ip':client_ip, 'protocol':protocol})
				restricted = True

			else:
				downloader = None
				content = None
				restricted = None

		except (ValueError, TypeError), e:
			logger.error('download', 'problem getting content %s %s' % (type(e),str(e)))
			downloader = None
			content = None
			restricted = None

		if downloader is not None:
			self.opening[downloader.sock] = downloader
			self.byclientid[downloader.client_id] = downloader

		return content, restricted


	def startDownload(self, sock):
		# shift the downloader to the other connected sockets
		downloader = self.opening.pop(sock, None)
		if downloader:
			self.established[sock] = downloader
			res = downloader.startConversation()
		else:
			res = None, None

		return res

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
			buffered = downloader.writeData(data)
			
			if buffered:
				if sock not in self.buffered:
					self.buffered.append(sock)
			elif had_buffer and sock in self.buffered:
				self.buffered.remove(sock)

			res = True
		else:
			res = False

                return res

	def sendClientData(self, client_id, data):
		downloader = self.byclientid.get(client_id, None)
		if downloader:
			if downloader.sock in self.established:
				had_buffer = True if downloader.w_buffer else False
				buffered = downloader.writeData(data)
			
				if buffered:
					if sock not in self.buffered:
						self.buffered.append(sock)
				elif had_buffer and sock in self.buffered:
					self.buffered.remove(sock)

				res = True

			elif downloader.sock in self.opening:
				buffered = downloader.bufferData(data)
				if downloader.sock not in self.buffered:
					self.buffered.append(downloader.sock)
	
				res = True

			else:  # what is going on if we reach this point
				self._terminate(downloader.sock, client_id)
				res = False
		else:
			res = False


		return res


	def endClientDownload(self, client_id):
		downloader = self.byclientid.get(client_id, None)
		if downloader:
			res = self._terminate(downloader.sock, client_id)
		else:
			res = False

		return res

	def _terminate(self, sock, client_id):
		downloader = self.established.get(sock, None)
		if downloader is None:
			downloader = self.opening.get(sock, None)

		if downloader:
			downloader.shutdown()

			self.established.pop(sock, None)
			self.opening.pop(sock, None)
			self.byclientid.pop(client_id, None)

			if sock in self.buffered:
				self.buffered.remove(sock)

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

		return True

