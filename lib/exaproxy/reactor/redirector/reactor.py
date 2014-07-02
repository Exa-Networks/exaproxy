# encoding: utf-8
"""
reactor.py

Created by David Farrar on 2014-03-17.
Copyright (c) 2011-2014 Exa Networks. All rights reserved.
"""

from exaproxy.util.log.logger import Logger


def debug (item, message):
	print '*' * 40 + ' ' + str(message)
	print str(item)
	print '*' * 40
	print

class RedirectorReactor (object):
	def __init__ (self, configuration, querier, decider, logger, usage, poller):
		self.querier = querier    # Incoming requests from the proxy
		self.decider = decider    # Decides how each request should be handled
		self.logger = logger      # Log writing interfaces
		self.usage = usage
		self.poller = poller

		# NOT the same logger the rest of the proxy uses since we're running in a different process
		self.log = Logger('redirector', configuration.log.supervisor)
		self.running = True

	def run(self):
		self.running = True

		# we may have new workers to deal with queued requests
		client_id, command, decision = self.decider.doqueue()
		while client_id is not None:
			self.querier.sendResponse(client_id, command, decision)
			client_id, command, decision = self.decider.doqueue()

		while self.running:
			# wait until we have something to do
			events = self.poller.poll()

			if events.get('control'):
				break

			# new requests
			if events.get('read_request'):
				try:
					message = self.querier.getRequest()
				except Exception, e:
					message = None

				if message is None:
					return False

				client_id, peer, header, subheader, source = message
				_, command, decision = self.decider.request(client_id, peer, header, subheader, source)

				if command is not None:
					self.querier.sendResponse(client_id, command, decision)

			# decisions made by the child processes
			for worker in events.get('read_workers', []):
				client_id, command, decision = self.decider.getDecision(worker)
				if client_id is not None:
					self.querier.sendResponse(client_id, command, decision)

			# we should have available workers now so check for queued requests
			for worker in events.get('read_workers', []):
				client_id, command, decision = self.decider.doqueue()

				if command is not None:
					self.querier.sendResponse(client_id, command, decision)

			self.logger.writeMessages()
			self.usage.writeMessages()

		return True
