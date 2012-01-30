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

		start_time = time.time()
		while self.running:
			t1 = time.time()
			# wait until we have something to do
			read, write, exceptional = poller.poll()

			t2 = time.time()

			if exceptional:
				logger.error('server','select returns some exceptional sockets %s' % str(exceptional))

			# handle new connections before anything else
			for sock in read['read_socks']:
				logger.info('server','new connection')
				for s, peer in self.server.accept(sock):
					logger.debug('server', 'new connection from %s' % str(peer))
					self.client.newConnection(s, peer)


			# incoming new requests from clients
			for client in read['opening_client']:
				client_id, peer, request, data = self.client.readRequest(client)
				if request:
					# we have a new request - decide what to do with it
					self.decider.request(client_id, peer, request)

				elif data:
					# we have data to send but very probably no server to send it to
					logger.error('server', 'Read content data along with the initial request from peer %s. It will likely be lost.' % str(peer))


			# incoming data from clients
			for client in read['read_client']:
				client_id, peer, request, data = self.client.readDataBySocket(client)
				if request:
					# XXX: We would need to put the client back in the 'opening' state
					#      here to ensure that no further data is read from the client
					#      until we successfully connect to the required server
					logger.error('server', 'Received multiple requests from peer %s. We do not handle this case yet. Closing the connection' % str(peer))
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
			for fetcher in read['read_download']:
				client_id, page_data = self.content.readData(fetcher)

				if page_data is None:
					logger.debug('server', 'lost connection to server while downloading for client id %s' % client_id)

				# send received data to the client that requested it
				status, flipflop = self.client.sendDataByName(client_id, page_data)

				# check to see if the client went away
				if status is None:
					if page_data is not None:
						logger.debug('server', 'client %s went away but we kept on downloading data' % client_id)
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
			for worker in read['read_workers']:
				logger.info('server','incoming decision')
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

				else:
					logger.debug('server', 'a decision was made for unknown client %s - perhaps it already disconnected?' % client_id)

			# clients we can write buffered data to
			for client in write['write_client']:
				status, flipflop, name = self.client.sendDataBySocket(client, '')

				if flipflop:
					# status should be False - we're here because we flushed buffered data
					if not status:    # No buffer
						self.content.uncorkClientDownload(name)

					else:         # Buffering
						self.content.corkClientDownload(name)

			# remote servers we can write buffered data to
			for download in write['write_download']:
				logger.info('server','flushing')
				status, flipflop = self.content.sendSocketData(download, '')

				if flipflop:
					if status:
						self.client.corkUploadByName(client_id)
					else:
						self.client.uncorkUploadByName(client_id)

			# fully connected connections to remote web servers
			for fetcher in write['opening_download']:
				logger.info('server','starting download')
				client_id, response = self.content.startDownload(fetcher)
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

			t3 = time.time()

			s_times.append(t2 - t1)
			w_times.append(t3 - t2)
			count += 1

			if count >= 200:
				end_time = time.time()

				s_min = min(s_times)
				s_max = max(s_times)
				s_avg = sum(s_times)/len(s_times)
				s_total = sum(s_times)
				s_dev = math.sqrt(sum(((t-s_avg)**2) for t in s_times))

				w_min = min(w_times)
				w_max = max(w_times)
				w_avg = sum(w_times)/len(w_times)
				w_total = sum(w_times)
				w_dev = math.sqrt(sum(((t-w_avg)**2) for t in w_times))

				s_times = []
				w_times = []


				print "looped %d times in %f seconds" % (count, end_time-start_time)
				print "current client count is: %d" % len(self.client.bysock)
				print
				print "sleeping: average: %0.05f\tmin: %0.05f\tmax: %0.05f\tstdev: %0.06f\ttotal: %0.05f" % (s_avg, s_min, s_max, s_dev, s_total)
				print "working:  average: %0.05f\tmin: %0.05f\tmax: %0.05f\tstdev: %0.06f\ttotal: %0.05f" % (w_avg, w_min, w_max, w_dev, w_total)
				print
				print

				count = 0
				start_time = time.time()
			
			yield None

