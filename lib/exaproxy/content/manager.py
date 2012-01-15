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

class ContentManager (object):
	def __init__(self, location):
		self._html = {}
		self.download = Downloader()
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
			content = 'file', filename
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
					html = data.replace('\0', os.linesep)
				content = ('html', http(code,html))

			elif command == 'file':
				code, reason = args.split('\0', 1)
				content = self.getLocalContent(reason)

		except (ValueError, TypeError), e:
			logger.error('download', 'problem getting content %s %s' % type(e),str(e))
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
