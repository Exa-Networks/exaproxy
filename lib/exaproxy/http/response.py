#!/usr/bin/env python
# encoding: utf-8
"""
http.py

Created by Thomas Mangin on 2011-12-02.
Copyright (c) 2011 Exa Networks. All rights reserved.
"""

import os

from exaproxy.util.logger import logger

class HTTPResponse (object):
	__read,__write = os.pipe()

	def __init__  (self,cid,code,title,body):
		self.cid = cid
		self.code = code
		self.title = title
		self.body = body
		self._recv = self._fetch()

	def fileno (self):
		return self.__read

	def request (self):
		return True

	def fetch (self):
		return self._recv.next()

	def _fetch (self):
		yield _http(self.code,html._html(self.title,self.body))
		yield None
