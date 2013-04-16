# encoding: utf-8
"""
reactor.py

Created by Thomas Mangin on 2011-11-30.
Copyright (c) 2011-2013  Exa Networks. All rights reserved.
"""

# http://code.google.com/speed/articles/web-metrics.html

from exaproxy.util.log.logger import Logger


class Reactor(object):
	def __init__(self, configuration, web, proxy, decider, content, client, resolver, logger, usage, poller):
		self.web = web            # Manage listening web sockets
		self.proxy = proxy        # Manage listening proxy sockets
		self.decider = decider    # Task manager for handling child decider processes
		self.content = content    # The Content Download manager
		self.client = client      # Currently open client connections
		self.resolver = resolver  # The DNS query manager
		self.poller = poller      # Interface to the poller
		self.logger = logger      # Log writing interfaces
		self.usage = usage        # Request logging
		self.running = True       # Until we stop we run :)
		self.nb_events = 0L       # Number of events received
		self.nb_loops = 0L        # Number of loop iteration

		self.log = Logger('supervisor', configuration.log.supervisor)

	def run(self):
		self.running = True

		poller = self.poller

#		count = 0
#		s_times = []
#		w_times = []

		decisions = []

		# Manually timeout queries
		timedout = self.resolver.cleanup()
		for client_id, command, decision in timedout:
			decisions.append((client_id, command, decision))

		self.resolver.expireCache()

		while self.running:
			# wait until we have something to do
			events = poller.poll()

			self.nb_loops += 1
			for name,ev in events.items():
				self.nb_events += len(ev)

			self.log.debug('events : ' + ', '.join(events.keys()))

			# handle new connections before anything else
			for sock in events.get('read_proxy',[]):
				for s, peer in self.proxy.accept(sock):
					self.client.newConnection(s, peer, 'proxy')


			# handle new connections before anything else
			for sock in events.get('read_web',[]):
				for s, peer in self.web.accept(sock):
					self.client.newConnection(s, peer, 'web')


			# incoming opening requests from clients
			for client in events.get('opening_client',[]):
				client_id, peer, request, data, source = self.client.readRequest(client)

				if request:
					# we have a new request - decide what to do with it
					self.decider.request(client_id, peer, request, source)

				elif request is None and client_id is not None:
					if source == 'proxy':
						self.proxy.notifyClose(client)
					elif source == 'web':
						self.web.notifyClose(client)


			# incoming data from clients
			for client in events.get('read_client',[]):
				client_id, peer, request, data, source = self.client.readDataBySocket(client)
				if request:
					# we have a new request - decide what to do with it
					self.decider.request(client_id, peer, request, 'proxy')

				if data:
					# we read something from the client so pass it on to the remote server
					status, buffer_change = self.content.sendClientData(client_id, data)

					if buffer_change:
						if status:
							self.client.corkUploadByName(client_id)
						else:
							self.client.uncorkUploadByName(client_id)

				elif data is None and client_id is not None:
					self.content.endClientDownload(client_id)
					if source == 'proxy':
						self.proxy.notifyClose(client)
					elif source == 'web':
						self.web.notifyClose(client)


			# clients we can write buffered data to
			for client in events.get('write_client',[]):
				status, buffer_change, name, source = self.client.sendDataBySocket(client, '')

				if status is None and name is not None:
					self.content.endClientDownload(name)
					if source == 'proxy':
						self.proxy.notifyClose(client)
					elif source == 'web':
						self.web.notifyClose(client)

				if buffer_change:
					# status should be False - we're here because we flushed buffered data
					if not status:    # No buffer
						self.content.uncorkClientDownload(name)

					else:         # Buffering
						self.content.corkClientDownload(name)


			# incoming data - web pages
			for fetcher in events.get('read_download',[]):
				client_id, page_data = self.content.readData(fetcher)

				# send received data to the client that requested it
				status, buffer_change, client = self.client.sendDataByName(client_id, page_data)

				# check to see if the client went away
				if status is None and client is not None:
					# We just closed our connection to the client and need to count the disconnect.
					self.proxy.notifyClose(client_id)

					if page_data is not None:
						# The client disconnected? Close our connection to the remote webserver.
						# We'll be notified of the client disconnect so don't count it here
						self.content.endClientDownload(client_id)

				elif buffer_change:
					# status should be true here - we don't read from the server when buffering
					if status:      # Buffering
						self.content.corkClientDownload(client_id)

					else:            # No buffer
						self.content.uncorkClientDownload(client_id)


			# decisions made by the child processes
			for worker in events.get('read_workers',[]):
				client_id, command, decision = self.decider.getDecision(worker)

				# check that the client didn't get bored and go away
				if client_id in self.client:
					if self.resolver.resolves(command, decision):
						identifier, response = self.resolver.startResolving(client_id, command, decision)
						if response:
							cid, command, decision = response
							decisions.append((client_id, command, decision))

						# this can not be resolved (no dot in hostname)
						elif identifier == 'not-found':
							command, decision = self.decider.showNotFound()
							decisions.append((client_id, command, decision))
						# something went wrong
						elif identifier is None:
							command, decision = self.decider.showInternalError()
							decisions.append((client_id, command, decision))
					else:
						decisions.append((client_id, command, decision))

			# decisions with a resolved hostname
			for resolver in events.get('read_resolver', []):
				response = self.resolver.getResponse(resolver)
				if response:
					client_id, command, decision = response
					decisions.append((client_id, command, decision))

			# all decisions we are currently able to process
			for client_id, command, decision in decisions:
				# send the possibibly rewritten request to the server
				response, length, status, buffer_change = self.content.getContent(client_id, command, decision)

				if buffer_change:
					if status:
						self.client.corkUploadByName(client_id)
					else:
						self.client.uncorkUploadByName(client_id)

				# Signal to the client that we'll be streaming data to it or
				# give it the location of the local content to return.
				client, data, source = self.client.startData(client_id, response, length)

				# Check for any data beyond the initial headers that we may already
				# have read and cached
				if data:
					status, buffer_change = self.content.sendClientData(client_id, data)

					if buffer_change:
						if status:
							self.client.corkUploadByName(client_id)
						else:
							self.client.uncorkUploadByName(client_id)

				elif data is None and client is not None:
					self.content.endClientDownload(client_id)
					if source == 'proxy':
						self.proxy.notifyClose(client)
					elif source == 'web':
						self.web.notifyClose(client)


			# remote servers we can write buffered data to
			for download in events.get('write_download',[]):
				status, buffer_change, client_id = self.content.sendSocketData(download, '')

				if buffer_change:
					if status:
						self.client.corkUploadByName(client_id)
					else:
						self.client.uncorkUploadByName(client_id)


			# fully connected connections to remote web servers
			for fetcher in events.get('opening_download',[]):
				client_id, response, buffer_change = self.content.startDownload(fetcher)
				if buffer_change:
					self.client.uncorkUploadByName(client_id)

				if client_id in self.client:
					if response:
						status, buffer_change, client = self.client.sendDataByName(client_id, response)
						if status is None and client is not None:
							# We just closed our connection to the client and need to count the disconnect.
							self.proxy.notifyClose(client_id)

							if response is not None:
								self.content.endClientDownload(client_id)

						elif buffer_change:
							# status should be True if we're here
							if status:
								self.content.corkClientDownload(client_id)

							else:
								self.content.uncorkClientDownload(client_id)



			# DNS servers we still have data to write to (should be TCP only)
			for resolver in events.get('write_resolver', []):
				self.resolver.continueSending(resolver)

			decisions = []

#			# retry connecting - opportunistic
#			for client_id, decision in retry_download:
#				# if we have a temporary error, the others are likely to be too
#				if not self.content.retryDownload(client_id, decision):
#					break


			self.logger.writeMessages()
			self.usage.writeMessages()
