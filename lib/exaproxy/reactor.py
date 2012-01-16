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

from .network.poller import poll_select as poller
from .util.logger import logger

class Reactor(object):
	poller = staticmethod(poller)

	def __init__(self, server, decider, content, client):
		self.server = server		# Manage listening sockets
		self.decider = decider		# Task manager for handling child decider processes
		self.content = content	# the Content Download manager
		self.client = client	# currently open client connections
		self.running = True
		self._loop = None

	def run (self):
		if not self._loop:
			self._loop = self._run()
		self._loop.next()

	def _run(self,speed=2):
		while self.running:
			read_socks = list(self.server.socks)		# listening sockets
			read_workers = list(self.decider.workers)	# pipes carrying responses from the child processes

			read_client = list(self.client.bysock)	# active clients
			write_client = list(self.client.buffered)	# active clients that we already have buffered data to send to

			read_download = list(self.content.established) # Currently established connections
			write_download = list(self.content.buffered)   # established connections to servers for which we have data to send
			opening_download = list(self.content.opening)	# socket connected but not yet ready for write

			retry_download = list(self.content.retry)	# rewritten destination info that we were unable to connect to

			# wait until we have something to do
			read, write, exceptional = self.poller(read_socks + read_workers + read_client + read_download, opening_download + write_download + write_client, speed)

			if exceptional:
				logger.error('server','select returns some exceptional sockets %s' % str(exceptional))

			# handle new connections before anything else
			for sock in set(read_socks).intersection(read):
				logger.info('server','new connection')
				for name, s, peer in self.server.accept(sock):
					logger.debug('server', 'new connection from %s' % str(peer))
					self.client.newConnection(name, s, peer)

			# XXX: Need to make sure we do not check the client for data after we
			#      have the request, since we're not going to read it anyway
			# incoming data from clients
			for client in set(read_client).intersection(read):
				client_id, peer, request, data = self.client.readRequestBySocket(client)
				if request:
					# request classification
					self.decider.request(client_id, peer, request)
				elif request is None:
					# the client closed the connection so we stop downloading for it
					self.content.endClientDownload(client_id)
				elif data:
					self.content.sendClientData(client_id, data)

			# incoming data - web pages

			for fetcher in set(read_download).intersection(read):
				client_id, page_data = self.content.readData(fetcher)

				if page_data is None:
					logger.debug('server', 'lost connection to server while downloading for client id %s' % client_id)


				# send received data to the client that requested it
				sending = self.client.sendDataByName(client_id, page_data)

				# check to see if the client went away
				if sending is None and page_data is not None:
					logger.debug('server', 'client %s went away but we kept on downloading data' % client_id)
					# should we use the fetcher (socket) as an index here rather than the client id?
					# should we just wait for the next loop when we'll be notified of the client disconnect?
					self.content.endClientDownload(client_id)

			# decisions made by the child processes
			for worker in set(read_workers).intersection(read):
				logger.info('server','incoming decision')
				client_id, decision = self.decider.getDecision(worker)
				# check that the client didn't get bored and go away
				if client_id in self.client:
					response = self.content.getContent(client_id, decision)
					# signal to the client that we'll be streaming data to it or
					# give it the location of the local content to return
					sending = self.client.startData(client_id, response)

					# check to see if the client went away
					if sending is None:
						# XXX: should we just wait for the next loop when we'll be notified of the client disconnect?
						# XXX: always results in a miss if there is no download process
						self.content.endClientDownload(client_id)
				else:
					logger.debug('server', 'a decision was made for unknown client %s - perhaps it already disconnected?' % client_id)

			# clients we can write buffered data to
			for client in set(write_client).intersection(write):
				self.client.sendDataBySocket(client, '')

			# remote servers we can write buffered data to
			for download in set(write_download).intersection(write):
				logger.info('server','flushing')
				self.content.sendDataBySocket(download, '')

			# fully connected connections to remote web servers
			for fetcher in set(opening_download).intersection(write):
				logger.info('server','starting download')
				client_id, response = self.content.startDownload(fetcher)
				# XXX: need to make sure we DO NOT read past the first request from
				#      the client until after we perform this read
				# check that the client didn't get bored and go away
				if client_id in self.client:
					logger.info('server','this read should not block')
					client_id, peer, request, data = self.client.readRequestByName(client_id)
					if data:
						self.content.sendClientData(client_id, data)

					if response:
						self.client.sendDataByName(client_id, response)

			# retry connecting - opportunistic 
			for client_id, decision in retry_download:
				# if we have a temporary error, the others are likely to be too
				if not self.content.retryDownload(client_id, decision):
					break
			
			yield None

