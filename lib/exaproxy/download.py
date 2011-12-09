#!/usr/bin/env python
# encoding: utf-8
"""
downloader.py

Created by Thomas Mangin on 2011-12-01.
Copyright (c) 2011 Exa Networks. All rights reserved.
"""

from threading import Thread
from Queue import Empty

from .logger import Logger
logger = Logger()

from .http import HTTPFetcher,HTTPResponse

class Download (object):
	"""A Thread which download pages"""
	def __init__(self, download_pipe):
		self.download_pipe = download_pipe      # A queue used by the workers to tell us what to download
		self._download_loop = None              # The download co-routine
		self.connect = set()                    # New connections to establish
		self.open = set()                       # Connection established but not yet write able
		self.fetchers = set()                   # the http object to now use

	def newFetcher (self):
		_cid,action,host,_port,request = self.download_pipe.readline().replace('\\n','\n').replace('\\r','\r').split(' ',4)
		cid = int(_cid)
		port = int(_port)

		# XXX: what to do ..
		# http://tools.ietf.org/html/rfc2616#section-14.10

		if action == 'request':
			logger.download('we need to download something on %s:%d' % (host,port))
			self.connect.add(HTTPFetcher(request,cid,host,int(port)))
		elif action == 'response':
			logger.download('direct response to %s' % cid)
			self.fetchers.add(HTTPResponse(request,cid,host,int(port)))
		else:
			raise RuntimeError('%s is an invalid action' % action)

	def connectFetchers (self):
		for fetcher in set(self.connect):
			logger.download('sending request on behalf of %s' % fetcher.cid)
			# True if we finished sending the request to the web server
			if fetcher.connect():
				# We now need to read from this object in the select loop
				self.connect.remove(fetcher)
				self.open.add(fetcher)

	def available (self,fetcher):
		self.fetchers.add(fetcher)
		self.open.remove(fetcher)
	
	def finish (self,cid):
		self.connect.discard(cid)
		self.open.discard(cid)
		self.fetchers.discard(cid)

	def stop (self):
		self.connect = set()
		self.open = set()
		self.fetchers = set()
