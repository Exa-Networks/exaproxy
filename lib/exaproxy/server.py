#!/usr/bin/env python
# encoding: utf-8
"""
server.py

Created by Thomas Mangin on 2011-11-30.
Copyright (c) 2011 Exa Networks. All rights reserved.
"""

# http://code.google.com/speed/articles/web-metrics.html

import os
import struct
import time
import socket
import errno

from select import select

from .browsers import Browsers

from .util.logger import logger


_block_errs = set([
	errno.EAGAIN, errno.EWOULDBLOCK, errno.EINTR
])
_close_errs = set([
	errno.EBADF, errno.ECONNRESET, errno.ESHUTDOWN,
	errno.ECONNABORTED, errno.ECONNREFUSED,
	errno.ENOTCONN, errno.EPIPE, errno.ECONNRESET,
])

class SelectError (Exception):
	pass

class Server (object):
	def __init__ (self,download,manager,request_box,ip,port,timeout,backlog,speed):
		self.request_box = request_box  # were HTTP request should sent
		self.download = download        # the Download manager
		self.manager = manager
		
		self.io = None                  # The socket on which we are listening
		self.speed = speed              # How long do we wait in select when no data is available

		self.ip = ip                    # The ip we are listening on
		self.port = port                # The port we are listening on
		self.timeout = timeout          # The socket timeout (how long before we give up ..) -- XXX: 5 is too low
		self.backlog = backlog          # How many connection should the kernel buffer before refusing connections
	
		self.running = True             # Are we listening or have we finished
		self._server_loop = None        # Our co-routing loop

		self.browsers = Browsers()   # holds all currently open client connections

	def _ipv6 (self,addr):
		try:
			socket.inet_pton(socket.AF_INET6, addr)
		except socket.error:
			return False
		return True

	def start (self):
		try:
			if self._ipv6(self.ip):
				self.io = socket.socket(socket.AF_INET6, socket.SOCK_STREAM, socket.IPPROTO_TCP)
				try:
					self.io.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
					self.io.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
				except AttributeError:
					pass
				self.io.settimeout(self.timeout)
				self.io.bind((self.ip,self.port,0,0))
			else:
				self.io = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
				try:
					self.io.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
					self.io.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
				except AttributeError:
					passs
				self.io.settimeout(self.timeout)
				self.io.bind((self.ip,self.port))
				self.io.setblocking(0)
				self.io.listen(self.backlog)
		except socket.error, e:
			if e.errno == errno.EADDRINUSE:
				logger.server('could not listen, connection in use %s:%d' % (self.ip,self.port))
			if e.errno == errno.EADDRNOTAVAIL:
				logger.server('could not listen, invalid address %s:%d' % (self.ip,self.port))
			logger.server('could not listen on %s:%d - %s' % (self.ip,self.port,str(e)))
			self.close()

	def select (self,read,write):
		#logger.server("select on read  %s" % str(read))
		#logger.server("select on write %s" % str(write))
		try:
			r,w,e = select(read,write,read+write,self.speed)
			#logger.server("ready on read   %s" % str(r))
			#logger.server("ready on write  %s" % str(w))
			# XXX: check for errors on e
			return r + [_ for _ in read if _.fileno() == 0], w
		except socket.error, e:
			if e.errno in (errno.EAGAIN, errno.EINTR,errno.EWOULDBLOCK,errno.EINTR,): # blocking return
				logger.server("select not ready, errno %s" % str(e.errno))
				return [],[],[]
			if e.errno in (errno.EINVAL,errno.EBADF,): # fatal issues (please do not change this list)
				logger.server("select problem, errno %s" % str(e.errno))
				raise
			logger.server("select issue, debug it, errno %s" % str(e.errno))
			raise SelectError()
		except (ValueError,AttributeError,TypeError), e:
			logger.server("fatal error encountered during select - %s %s" % (type(e),str(e)))
			for obj in r:
				if not hasattr(obj,'fileno'):
					logger.server("a object without fileno() was passed to select")
				if obj.fileno() < 0:
					logger.server("PYPY 1.7 change socket object to return -1 when they are closed, this is an issue for us")
			raise SelectError()
		except Exception, e:
			logger.server("select problem, %s %s" % (type(e),str(e)))
			raise SelectError()

	def accept (self):
		while True:
			try:
				sock,peer = self.io.accept()
				self.browsers.newConnection(sock, peer)
				yield peer
			except socket.error, e:
				# errno.EINTR ? --> Interrupt can stop a read() we must then retry
				if e.errno in (errno.EAGAIN,errno.EWOULDBLOCK,errno.EINTR,):
					break
				logger.server('failure on accept %s' % str(e))
				yield None

	def stop (self):
		logger.server("stop server listening on %s:%s" % (self.ip,str(self.port)))
		self.running = False
		try:
			self.io.shutdown(socket.SHUT_RDWR)
			self.io.close()
		except socket.error:
			pass
		self.browsers.stop()

	def run (self):
		if self._server_loop is None:
			logger.server('starting')
			self._server_loop = self._run()
		elif self.running:
			self._server_loop.next()
		else:
			logger.server('can not run, stopped <server>')

	def _run (self):
		while self.running:
			read_workers = list(self.manager.workers)

			read_browser = list(self.browsers.established) # Newly established connections
			read_download = list(self.download.established) # Currently established connections
			write_opening = list(self.download.opening) # socket connected but not yet ready for write

#			print "read_browser ", read_browser
#			print "read_downlaod", read_download
#			print "read_workers ", read_workers
#			print "write_opening   ", write_opening 

			read,write = self.select([self.io] + read_workers + read_browser + read_download, write_opening)

			if read: print "read   [%s]" % read
			if write: print "write [%s]" % write

			# we have new connections
			if self.io in read:
				for peer in self.accept():
					if peer is None:
						# XXX: Thomas: is it wise to exit ?
						logger.server('could not accept new connection, exiting')
						self.running = False
						continue
					else:
						logger.server('new connection, %s' % str(peer))

			# some new connection became available to read
			for browser in set(read_browser).intersection(read):
				name, peer, request = self.browsers.readRequest(browser)
				if request:
					# request classification
					self.request_box.put((name, peer, request))

			for fetcher in set(read_download).intersection(read):
				# the connection to the client is still open
				if fetcher.cid in self.browsers.established_id():
					webpage = fetcher.fetch()
					# The webserver finished sending and closed the connection
					if webpage:
						logger.server('we fetched %d byte of data for client id %d' % (len(webpage),fetcher.cid))
						self.browsers.sendData(fetcher.cid, webpage)
						continue
					self.download.finish(fetcher)
					self.browsers.completed(fetcher.cid)
				# the client closed the connection
				else:
					# XXX: Handle cleanup automatically in the download class
					self.download.finish(fetcher)

			# should only be the one which are free to write
			for cid in self.browsers.canReply():
				left = self.browsers.sendData(cid,'')

			for pipe in set(read_workers).intersection(read):
				self.download.newFetcher(pipe)
			self.download.connectFetchers()

			# some socket are now available for write
			for fetcher in set(write_opening).intersection(write):
				if fetcher.request():
					self.download.available(fetcher)

#				response = fetcher.request()
#				if response:
#					self.download.available(fetcher)
#					continue
#				if response is None:
#					self.browsers.completed(fetcher.cid)
#					self.download.finish(fetcher)
#					continue

			self.browsers.close()
			yield None

		
