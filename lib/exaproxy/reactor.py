#!/usr/bin/env python
# encoding: utf-8
"""
server.py

Created by Thomas Mangin on 2011-11-30.
Copyright (c) 2011 Exa Networks. All rights reserved.
"""

# http://code.google.com/speed/articles/web-metrics.html

import time
import errno

from poller import poller_select
from .util.logger import logger


_close_errs = set([
	errno.EBADF, errno.ECONNRESET, errno.ESHUTDOWN,
	errno.ECONNABORTED, errno.ECONNREFUSED,
	errno.ENOTCONN, errno.EPIPE, errno.ECONNRESET,
])


class Reactor(object):
	select = staticmethod(poller_select)

	def __init__(self, server, decider, download, browsers):
		self.server = server		# Manage listening sockets
		self.decider = decider		# Task manager for handling child decider processes
		self.download = download	# the Download manager
		self.browsers = browsers	# currently open client connections

	def run(self, speed):
		running = True

		while running:
			read_socks = list(self.server.socks)		# listening sockets
			read_workers = list(self.decider.workers)	# pipes carrying responses from the child processes

			read_browser = list(self.browsers.clients)	# active clients
			write_browser = list(self.browsers.buffered)	# active clients that we already have buffered data to send to


			read_download = list(self.download.established) # Currently established connections
			write_download = list(self.download.buffered)   # established connections to servers for which we have data to send
			opening_download = list(self.download.opening)	# socket connected but not yet ready for write

			retry_download = list(self.download.retry)	# rewritten destination info that we were unable to connect to



			#print "*"*100
			#print "READABLE DOWNLOAD SOCKETS ARE:", read_download
			#print "BUFFERED DOWNLOAD SOCKETS ARE:", write_download
			#print "*"*100
			#print
			#print

			# wait until we have something to do
			read, write, x = self.select(read_socks + read_workers + read_browser + read_download, opening_download + write_download + write_browser, speed)

			if x:
				print "EXCEPTIONAL", x


			# handle new connections before anything else
			for sock in set(read_socks).intersection(read):
				print "**** NEW CONNECTION"
				for name, s, peer in self.server.accept(sock):
					logger.debug('server', 'new connection from %s' % str(peer))
					self.browsers.newConnection(name, s, peer)

			# XXX: Need to make sure we do not check the browser for data after we
			#      have the request, since we're not going to read it anyway
			# incoming data from browsers
			for browser in set(read_browser).intersection(read):
				client_id, peer, request, data = self.browsers.readRequest(browser)
				if request:
					# request classification
					self.decider.putRequest(client_id, peer, request)
				elif request is None:
					# the client closed the connection so we stop downloading for it
					self.download.endClientDownload(client_id)
				elif data:
					print "WANT TO SEND", len(data)
					self.download.sendClientData(client_id, data)

			# incoming data - web pages

			for fetcher in set(read_download).intersection(read):
				client_id, page_data = self.download.readData(fetcher)

				if page_data is None:
					logger.debug('server', 'lost connection to server while downloading for client id %s' % client_id)


				# send received data to the client that requested it
				sending = self.browsers.sendData(client_id, page_data)

				# check to see if the client went away
				if sending is None and page_data is not None:
					logger.debug('server', 'client %s went away but we kept on downloading data' % client_id)
					# should we use the fetcher (socket) as an index here rather than the client id?
					# should we just wait for the next loop when we'll be notified of the client disconnect?
					self.download.endClientDownload(client_id)

			# decisions made by the child processes
			for worker in set(read_workers).intersection(read):
				print "*** INCOMING DECISION"
				client_id, decision = self.decider.getDecision(worker)
				print "*** GOT DECISION", client_id in self.browsers
				# check that the client didn't get bored and go away
				if client_id in self.browsers:
					response = self.download.getContent(client_id, decision)
					print 'RESPONSE START IS', response
					# signal to the client that we'll be streaming data to it or
					# give it the location of the local content to return
					sending = self.browsers.startData(client_id, response)

					# check to see if the client went away
					if sending is None:
						# XXX: should we just wait for the next loop when we'll be notified of the client disconnect?
						# XXX: always results in a miss if there is no download process
						self.download.endClientDownload(client_id)
				else:
					logger.debug('server', 'a decision was made for unknown client %s - perhaps it already disconnected?' % client_id)

			# browsers we can write buffered data to
			for browser in set(write_browser).intersection(write):
				self.browsers.sendSocketData(browser, '')

			# remote servers we can write buffered data to
			for download in set(write_download).intersection(write):
				print "FLUSHING", download
				self.download.sendSocketData(download, '')

			# fully connected connections to remote web servers
			for fetcher in set(opening_download).intersection(write):
				print "*** STARTING DOWNLOAD"
				self.download.startDownload(fetcher)

			# retry connecting - opportunistic 
			for client_id, decision in retry_download:
				# if we have a temporary error, the others are likely to be too
				if not self.download.retryDownload(client_id, decision):
					break

