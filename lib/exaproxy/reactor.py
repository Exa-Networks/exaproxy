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
import math

from .util.logger import logger


class Reactor(object):
	def __init__(self, server, decider, content, client, poller):
		self.server = server		# Manage listening sockets
		self.decider = decider		# Task manager for handling child decider processes
		self.content = content		# the Content Download manager
		self.client = client		# currently open client connections
		self.poller = poller		# Interface to the poller
		self.running = True
		self._loop = None

	def run (self):
		if not self._loop:
			self._loop = self._run()
		self._loop.next()

	def _run(self):
		poller = self.poller

		count = 0
		s_times = []
		w_times = []

		while self.running:
			# wait until we have something to do
			events = poller.poll()

			# handle new connections before anything else
			for sock in events['read_socks']:
				for s, peer in self.server.accept(sock):
					self.client.newConnection(s, peer)


			# incoming new requests from clients
			for client in events['opening_client']:
				client_id, peer, request, data = self.client.readRequest(client)
				if request:
					# we have a new request - decide what to do with it
					self.decider.request(client_id, peer, request)



			# incoming data from clients
			for client in events['read_client']:
				client_id, peer, request, data = self.client.readDataBySocket(client)
				if request:
					# XXX: We would need to put the client back in the 'opening' state
					#      here to ensure that no further data is read from the client
					#      until we successfully connect to the required server
					# XXX: should we allow cleanup to be called outside of the manager?
					self.client.cleanup(client)

				elif data:
					# we read something from the client so pass it on to the remote server
					status, flipflop = self.content.sendClientData(client_id, data)

					if flipflop:
						if status:
							self.client.corkUploadByName(client_id)
						else:
							self.client.uncorkUploadByName(client_id)

					# XXX: sendClientData() should tell us whether or not the socket was
					#      added to / removed from the buffer list

				elif data is None:
					self.content.endClientDownload(client_id)

					
			# incoming data - web pages
			for fetcher in events['read_download']:
				client_id, page_data = self.content.readData(fetcher)

				# send received data to the client that requested it
				status, flipflop = self.client.sendDataByName(client_id, page_data)

				# check to see if the client went away
				if status is None:
					if page_data is not None:
						# should we use the fetcher (socket) as an index here rather than the client id?
						# should we just wait for the next loop when we'll be notified of the client disconnect?
						self.content.endClientDownload(client_id)

				elif flipflop:
					# status should be true here - we don't read from the server when buffering
					if status:      # Buffering
						self.content.corkClientDownload(client_id)

					else:            # No buffer
						self.content.uncorkClientDownload(client_id)

			# decisions made by the child processes
			for worker in events['read_workers']:
				client_id, decision = self.decider.getDecision(worker)

				# check that the client didn't get bored and go away
				if client_id in self.client:
					response, restricted = self.content.getContent(client_id, decision)

					# Signal to the client that we'll be streaming data to it or
					# give it the location of the local content to return.
					data = self.client.startData(client_id, response, restricted)

					# Check for any data beyond the initial headers that we may already
					# have read and cached
					if data:
						status, flipflop = self.content.sendClientData(client_id, data)

						if flipflop:
							if status:
								self.client.corkUploadByName(client_id)
							else:
								self.client.uncorkUploadByName(client_id)

					# XXX: client should prune itself
					elif data is None:
						self.content.endClientDownload(client_id)


			# clients we can write buffered data to
			for client in events['write_client']:
				status, flipflop, name = self.client.sendDataBySocket(client, '')

				if flipflop:
					# status should be False - we're here because we flushed buffered data
					if not status:    # No buffer
						self.content.uncorkClientDownload(name)

					else:         # Buffering
						self.content.corkClientDownload(name)

			# remote servers we can write buffered data to
			for download in events['write_download']:
				status, flipflop = self.content.sendSocketData(download, '')

				if flipflop:
					if status:
						self.client.corkUploadByName(client_id)
					else:
						self.client.uncorkUploadByName(client_id)

			# fully connected connections to remote web servers
			for fetcher in events['opening_download']:
				client_id, response, flipflop = self.content.startDownload(fetcher)
				if flipflop:
					self.client.uncorkUploadByName(client_id)

				if client_id in self.client:
					if response:
						status, flipflop = self.client.sendDataByName(client_id, response)
						if flipflop:
							# status should be True if we're here
							if status:
								self.content.corkClientDownload(client_id)

							else:
								self.content.uncorkClientDownload(client_id)

#			# retry connecting - opportunistic 
#			for client_id, decision in retry_download:
#				# if we have a temporary error, the others are likely to be too
#				if not self.content.retryDownload(client_id, decision):
#					break

			
			yield None

