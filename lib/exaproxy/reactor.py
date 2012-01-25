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
		self.content = content		# the Content Download manager
		self.client = client		# currently open client connections
		self.running = True
		self._loop = None

	def run (self):
		if not self._loop:
			self._loop = self._run()
		self._loop.next()

	def _run(self,speed=2):
		while self.running:
			read_socks = tuple(self.server.socks)		# listening sockets
			read_workers = tuple(self.decider.workers)	# pipes carrying responses from the child processes

			read_client = tuple(self.client.bysock)	        # active clients
			write_client = tuple(self.client.buffered)	# active clients that we already have buffered data to send to
			opening_client = tuple(self.client.norequest)    # clients we have not yet read a request from

			read_download = tuple(self.content.established)  # Currently established connections
			write_download = tuple(self.content.buffered)    # established connections to servers for which we have data to send
			opening_download = tuple(self.content.opening)	# socket connected but not yet ready for write

			retry_download = tuple(self.content.retry)	# rewritten destination info that we were unable to connect to

			# wait until we have something to do
			read, write, exceptional = self.poller(read_socks + read_workers + read_client + read_download + opening_client, opening_download + write_download + write_client, speed)

			if exceptional:
				logger.error('server','select returns some exceptional sockets %s' % str(exceptional))

			# handle new connections before anything else
			for sock in set(read_socks).intersection(read):
				logger.info('server','new connection')
				for s, peer in self.server.accept(sock):
					logger.debug('server', 'new connection from %s' % str(peer))
					self.client.newConnection(s, peer)

				# REGENERATE: read_socks=self.server.socks

			# incoming new requests from clients
			for client in set(opening_client).intersection(read):
				client_id, peer, request, data = self.client.readRequest(client)
				if request:
					# we have a new request - decide what to do with it
					self.decider.request(client_id, peer, request)

				elif data:
					# we have data to send but very probably no server to send it to
					logger.error('server', 'Read content data along with the initial request from peer %s. It will likely be lost.' % str(peer))

				# REGENERATE: opening_client iif request is None


			# incoming data from clients
			for client in set(read_client).intersection(read):
				client_id, peer, request, data = self.client.readDataBySocket(client)
				if request:
					# XXX: We would need to put the client back in the 'opening' state
					#      here to ensure that no further data is read from the client
					#      until we successfully connect to the required server
					logger.error('server', 'Received multiple requests from peer %s. We do not handle this case yet. Closing the connection' % str(peer))
					# XXX: should we allow cleanup to be called outside of the manager?
					self.client.cleanup(client)
					# REGENERATE: read_client, write_client
					# REGENERATE: opening_client since we're doing everything else anyway?

				elif data:
					# we read something from the client so pass it on to the remote server
					self.content.sendClientData(client_id, data)

					# XXX: sendClientData() should tell us whether or not the socket was
					#      added to / removed from the buffer list
					# REGENERATE: write_download

				elif data is None:
					self.content.endClientDownload(client_id)

					# REGENERATE: read_client, write_client,    read_download, write_download, opening_download
					# REGENERATE: opening_client since we're doing everything else anyway?
					
			# incoming data - web pages
			for fetcher in set(read_download).intersection(read):
				client_id, page_data = self.content.readData(fetcher)

				if page_data is None:
					logger.debug('server', 'lost connection to server while downloading for client id %s' % client_id)

					# REGENERATE: read_download, write_download

				# send received data to the client that requested it
				sending = self.client.sendDataByName(client_id, page_data)

				# check to see if the client went away
				if sending is None:
					if page_data is not None:
						logger.debug('server', 'client %s went away but we kept on downloading data' % client_id)
						# should we use the fetcher (socket) as an index here rather than the client id?
						# should we just wait for the next loop when we'll be notified of the client disconnect?
						self.content.endClientDownload(client_id)

					# REGENERATE: read_client, write_client

			# decisions made by the child processes
			for worker in set(read_workers).intersection(read):
				logger.info('server','incoming decision')
				client_id, decision = self.decider.getDecision(worker)

				# check that the client didn't get bored and go away
				if client_id in self.client:
					response, restricted = self.content.getContent(client_id, decision)

					# REGENERATE: opening_download iif command == 'stream'

					# Signal to the client that we'll be streaming data to it or
					# give it the location of the local content to return.
					data = self.client.startData(client_id, response, restricted)

					# Check for any data beyond the initial headers that we may already
					# have read and cached
					if data:
						# REGENERATE: write_client  -- startData should tell us whether or not we need to do this

						self.content.sendClientData(client_id, data)

						# REGENERATE: write_download -- sendClientData should tell us whether or not we need to do this
						# REGENERATE: If there's an error sending to the server then we ignore it here and pick it up
						#             on the next loop when trying to read from it. Double check that this is ok

					# XXX: client should prune itself
					elif data is None:
						# REGENERATE: read_client, write_client

						self.content.endClientDownload(client_id)

						# REGENERATE: read_download, write_download, opening_download
				else:
					logger.debug('server', 'a decision was made for unknown client %s - perhaps it already disconnected?' % client_id)

			# clients we can write buffered data to
			for client in set(write_client).intersection(write):
				self.client.sendDataBySocket(client, '')
				# REGENERATE: write_client

			# remote servers we can write buffered data to
			for download in set(write_download).intersection(write):
				logger.info('server','flushing')
				self.content.sendSocketData(download, '')
				# REGENERATE: write_download

			# fully connected connections to remote web servers
			for fetcher in set(opening_download).intersection(write):
				logger.info('server','starting download')
				client_id, response = self.content.startDownload(fetcher)
				# REGENERATE: opening_download, write_download, read_download ???
				if client_id in self.client:
					if response:
						self.client.sendDataByName(client_id, response)
						# REGENERATE: write_client
						# REGENERATE: handling errors in read on next loop?

			# retry connecting - opportunistic 
			for client_id, decision in retry_download:
				# if we have a temporary error, the others are likely to be too
				if not self.content.retryDownload(client_id, decision):
					break
			
			yield None

