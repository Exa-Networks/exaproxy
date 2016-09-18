# encoding: utf-8
"""
reactor.py

Created by Thomas Mangin on 2011-11-30.
Copyright (c) 2011-2013  Exa Networks. All rights reserved.
"""

# http://code.google.com/speed/articles/web-metrics.html

from exaproxy.util.log.logger import Logger


class StopReactor (Exception):
	pass


class Reactor (object):
	handlers = {}

	def __init__(self, configuration, web, proxy, passthrough, icap, tls, decider, content, client, resolver, logger, usage, poller):
		self.web = web                 # Manage listening web sockets
		self.proxy = proxy             # Manage listening proxy sockets
		self.passthrough = passthrough # Manage listening raw data sockets
		self.icap = icap               # Manage listening icap sockets
		self.tls = tls                 # Manage listening tls sockets
		self.decider = decider         # Task manager for handling child decider processes
		self.content = content         # The Content Download manager
		self.client = client           # Currently open client connections
		self.resolver = resolver       # The DNS query manager
		self.poller = poller           # Interface to the poller
		self.logger = logger           # Log writing interfaces
		self.usage = usage             # Request logging
		self.nb_events = 0L            # Number of events received
		self.nb_loops = 0L             # Number of loop iteration
		self.events = []               # events so we can report them once in a while

		self.log = Logger('supervisor', configuration.log.supervisor)

	def register (event, handlers=handlers):
		def decorator (method):
			handlers[event] = method
			return method

		return decorator

	@register('read_proxy')
	def acceptProxyConnections (self, socks):
		for sock in socks:
			for s, peer in self.proxy.accept(sock):
				self.client.httpConnection(s, peer, 'proxy')

	@register('read_icap')
	def acceptICAPConnections (self, socks):
		for sock in socks:
			for s, peer in self.icap.accept(sock):
				self.client.icapConnection(s, peer, 'icap')

	@register('read_tls')
	def acceptTLSConnections (self, socks):
		for sock in socks:
			for s, peer in self.tls.accept(sock):
				self.client.tlsConnection(s, peer, 'tls')

	@register('read_passthrough')
	def acceptPassthroughConnections (self, socks):
		for sock in socks:
			for s, peer in self.passthrough.accept(sock):
				client_id, accept_addr, accept_port = self.client.passthroughConnection(s, peer, 'passthrough')

				self.decider.sendRequest(client_id, accept_addr, accept_port, peer, '', '', 'passthrough')

	@register('read_web')
	def acceptAdminConnections (self, socks):
		for sock in socks:
			for s, peer in self.web.accept(sock):
				self.client.httpConnection(s, peer, 'web')

	def closeClient (self, client, source):
		if source == 'proxy':
			self.proxy.notifyClose(client)

		elif source == 'icap':
			self.icap.notifyClose(client)

		elif source == 'passthrough':
			self.passthrough.notifyClose(client)

		elif source == 'tls':
			self.tls.notifyClose(client)

		elif source == 'passthrough':
			self.passthrough.notifyClose(client)

		elif source == 'web':
			self.web.notifyClose(client)

	@register('opening_client')
	def incomingRequest (self, clients):
		for client in clients:
			client_id, accept_addr, accept_port, peer, request, subrequest, data, source = self.client.readRequest(client)

			if request:
				# we have a new request - decide what to do with it
				self.decider.sendRequest(client_id, accept_addr, accept_port, peer, request, subrequest, source)

			elif request is None and client_id is not None:
				self.closeClient(client, source)

	@register('read_client')
	def incomingClientData (self, clients):
		for client in clients:
			client_id, accept_addr, accept_port, peer, request, subrequest, data, source = self.client.readData(client)

			if request:
				# we have a new request - decide what to do with it
				self.decider.sendRequest(client_id, accept_addr, accept_port, peer, request, subrequest, source)

			if data:
				# we read something from the client so pass it on to the remote server
				status, buffer_change = self.content.sendClientData(client, data)

				if buffer_change:
					if status:
						self.client.corkUpload(client)
					else:
						self.client.uncorkUpload(client)

			elif data is None and client_id is not None:
				self.content.endClientDownload(client)
				self.closeClient(client, source)

	@register('write_client')
	def flushClientOutput (self, clients):
		for client in clients:
			status, buffer_change, name, source = self.client.sendData(client, '')

			if status is None and name is not None:
				self.content.endClientDownload(client)

				if source == 'proxy':
					self.proxy.notifyClose(client)

				elif source == 'icap':
					self.icap.notifyClose(client)

				elif source == 'passthrough':
					self.passthrough.notifyClose(client)

				elif source == 'tls':
					self.tls.notifyClose(client)

				elif source == 'passthrough':
					self.passthrough.notifyClose(client)

				elif source == 'web':
					self.web.notifyClose(client)

			if buffer_change:
				# status should be False - we're here because we flushed buffered data
				if not status:    # No buffer
					self.content.uncorkClientDownload(client)

				else:         # Buffering
					self.content.corkClientDownload(client)


	@register('opening_download')
	def completeWebConnection (self, fetchers):
		for fetcher in fetchers:
			client, response, buffer_change = self.content.startDownload(fetcher)
			if buffer_change:
				self.client.uncorkUpload(client)

			if client in self.client:
				if response:
					status, buffer_change, name, source = self.client.sendData(client, response)
					if status is None and client is not None:
						# We just closed our connection to the client and need to count the disconnect.
						if source == 'proxy':
							self.proxy.notifyClose(client)

						elif source == 'tls':
							self.tls.notifyClose(client)

						elif source == 'passthrough':
							self.passthrough.notifyClose(client)

						if response is not None:
							self.content.endClientDownload(client)

					elif buffer_change:
						# status should be True if we're here
						if status:
							self.content.corkClientDownload(client)

						else:
							self.content.uncorkClientDownload(client)

	@register('read_download')
	def incomingWebData (self, fetchers):
		for fetcher in fetchers:
			client, page_data = self.content.readData(fetcher)

			# send received data to the client that requested it
			status, buffer_change, name, source = self.client.sendData(client, page_data)

			# check to see if the client went away
			if status is None and client is not None:
				# We just closed our connection to the client and need to count the disconnect.
				if source == 'proxy':
					self.proxy.notifyClose(client)

				elif source == 'tls':
					self.tls.notifyClose(client)

				elif source == 'passthrough':
					self.passthrough.notifyClose(client)

				if page_data is not None:
					# The client disconnected? Close our connection to the remote webserver.
					# We'll be notified of the client disconnect so don't count it here
					self.content.endClientDownload(client)

			elif buffer_change:
				# status should be true here - we don't read from the server when buffering
				if status:      # Buffering
					self.content.corkClientDownload(client)

	@register('write_download')
	def flushWebOutput (self, fetchers):
		for fetcher in fetchers:
			status, buffer_change, client = self.content.sendSocketData(fetcher, '')

			if buffer_change:
				if status:
					self.client.corkUpload(client)

				else:
					self.client.uncorkUpload(client)


	@register('read_redirector')
	def readRedirector (self, deciders):
		for decider in deciders:
			name, command, decision = self.decider.getDecision()
			client = self.client.lookupSocket(name)

			if command is None:
				# if the redirector process disappears then we must close the proxy
				raise StopReactor

			# check that the client didn't get bored and go away
			if client is not None:
				if self.resolver.resolves(command, decision):
					identifier, response = self.resolver.startResolving(client, command, decision)
					if response:
						_client, command, decision = response[0], response[1], response[2:]
						yield client, command, decision

					# something went wrong
					elif identifier is None:
						command, decision = self.decider.showInternalError()
						yield client, command, decision

				else:
					yield client, command, decision

	@register('read_resolver')
	def readResolver (self, resolvers):
		for resolver in resolvers:
			response = self.resolver.getResponse(resolver)
			if response:
				client, command, decision = response[0], response[1], response[2:]
				yield client, command, decision

	@register('write_resolver')
	def flushResolver (self, resolvers):
		for resolver in resolvers:
			self.resolver.continueSending(resolver)

	def timeoutResolver (self):
		timedout = self.resolver.cleanup()

		for client, command, decision in timedout:
			yield client, command, decision

	def enactDecisions (self, decisions):
		for client, command, decision in decisions:
			response, length, status, buffer_change = self.content.getContent(client, command, decision)

			if buffer_change:
				if status:
					self.client.corkUpload(client)

				else:
					self.client.uncorkUpload(client)

			# Signal to the client that we'll be streaming data to it or
			# give it the location of the local content to return.
			data, source = self.client.startData(client, response, length)

			# Check for any data beyond the initial headers that we may already
			# have read and cached
			if data:
				status, buffer_change = self.content.sendClientData(client, data)

				if buffer_change:
					if status:
						self.client.corkUpload(client)

					else:
						self.client.uncorkUpload(client)

			elif data is None and client is not None:
				self.content.endClientDownload(client)
				self.closeClient(client, source)


	def handle (self, event, interfaces):
		handler = self.handlers.get(event, None)
		if not handler:
			return None

		return handler(self, interfaces)


	def run (self):
		poller = self.poller

		interrupt_events = {'read_interrupt', 'read_control'}
		received_interrupts = set()

		# look for any DNS requests that are taking too long so we can
		# notify the client of the problem
		decisions = self.timeoutResolver()
		self.enactDecisions(decisions)

		self.resolver.expireCache()


		try:
			while True:
				# wait until we have something to do
				events = poller.poll()
				self.events = events

				self.nb_loops += 1

				for event, interfaces in events.items():
					self.nb_events += len(interfaces)

					decisions = self.handle(event, interfaces) if interfaces else []
					if decisions:
						self.enactDecisions(decisions)

				self.logger.writeMessages()
				self.usage.writeMessages()

				received_interrupts = {k for k in interrupt_events if events.get(k)}
				if received_interrupts:
					break

		except StopReactor:
			return False, {}

		return True, received_interrupts
