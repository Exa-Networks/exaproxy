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
		self._html = {}

	def getLocalContent(self, name):
		if not name.startswith('/'):
			filename = os.path.join(self.location, name)
		else:
			filename = name
		if os.path.isfile(filename):
			content = 'file', filename
		else: 
			logger.debug('download', 'no file exists for %s: %s' % (str(name), str(filename)))
			content = None

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
				headers = 'HTTP/1.1 302 Surfprotected\r\nLocation: http://%s\r\n\r\n\r\n' % redirect_url

				downloader = None
				content = ('close', headers)
				restricted = True

			elif command == 'html':
				code, data = args.split('\0', 1)
				if data.startswith('file://'):
					name = data[7:]
					if name in self._html:
						html = self._html[name]
					else:
						if name.startswith('/'):
							fname = name
						else:
							fname = os.path.normpath(os.path.join(self.location,name))
						if not fname.startswith(self.location):
							html = 'invalid file location for %s' % name
						else:
							try:
								with open(fname,'r') as f:
									html = f.read()
								self._html[name] = html
							except IOError:
								html = 'could not open %s' % name
				else:
					html = data

				downloader = None
				content = ('close', http(code,html))
				restricted = True

			elif command == 'file':
				code, reason = args.split('\0', 1)
				downloader = None
				content = self.getLocalContent(reason)
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
			# XXX: what do we do if this happens?
			if (downloader.sock, downloader.client_id) != (sock, client_id):
				raise BadError

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
		# XXX: Fixme
		print "STOP exists to not cause close warning"
		pass
