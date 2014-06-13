# encoding: utf-8
"""
process.py

Created by Thomas Mangin on 2011-11-29.
Copyright (c) 2011-2013  Exa Networks. All rights reserved.
"""

# prevent persistence : http://tools.ietf.org/html/rfc2616#section-8.1.2.1
# NOTE: We may have more than one Connection header : http://tools.ietf.org/html/rfc2616#section-14.10
# NOTE: We may need to remove every step-by-step http://tools.ietf.org/html/rfc2616#section-13.5.1
# NOTE: We NEED to respect Keep-Alive rules http://tools.ietf.org/html/rfc2068#section-19.7.1
# NOTE: We may look at Max-Forwards

import os
import time

from .child import ChildFactory
from .response import ResponseFactory
from .response import ResponseEncoder as Respond

from exaproxy.http.message import HTTP
from exaproxy.http.response import http
from exaproxy.http.factory import HTTPRequestFactory

from exaproxy.util.log.logger import Logger
from exaproxy.util.log.logger import UsageLogger

from exaproxy.util.log.history import Errors,History,Level

class Redirector:
	# TODO : if the program is a function, fork and run :)
	HTTPParser = HTTPRequestFactory
	ResponseFactory = ResponseFactory
	ChildFactory = ChildFactory

	def __init__ (self, configuration, name, program, protocol):
		self.configuration = configuration
		self.http_parser = self.HTTPParser(configuration)
		self.enabled = bool(program is not None)
		self._transparent = configuration.http.transparent
		self.log = Logger('worker ' + str(name), configuration.log.worker)
		self.usage = UsageLogger('usage', configuration.log.worker)
		self.response_factory = self.ResponseFactory()
		self.child_factory = self.ChildFactory(configuration, name)

		self.wid = name							   # a unique name
		self.creation = time.time()				   # when the thread was created
	#	self.last_worked = self.creation			  # when the thread last picked a task

		self.program = program						# the squid redirector program to fork
		self.running = True						   # the thread is active

		self.stats_timestamp = None				   # time of the most recent outstanding request to generate stats

		self._proxy = 'ExaProxy-%s-id-%d' % (configuration.proxy.version,os.getpid())

		universal = configuration.redirector.protocol == 'url'
		# Do not move, we need the forking AFTER the setup
		self.process = self.child_factory.createProcess(self.program, universal=universal)

	def addHeaders (self, message, peer):
		headers = message.headers
		# http://homepage.ntlworld.com./jonathan.deboynepollard/FGA/web-proxy-connection-header.html
		headers.pop('proxy-connection',None)
		# NOTE: To be RFC compliant we need to add a Via field http://tools.ietf.org/html/rfc2616#section-14.45 on the reply too
		# NOTE: At the moment we only add it from the client to the server (which is what really matters)
		if not self._transparent:
			headers.extend('via','Via: %s %s' % (message.request.version, self._proxy))
			headers.extend('x_forwarded_for', 'X-Forwarded-For: %s' % peer)
			headers.pop('proxy-authenticate')

		return message

	def checkChild (self):
		if self.enabled:
			ok = bool(self.process) and self.process.poll() is None

		else:
			ok = True

		return ok

	def writeChild (self, request_string):
		try:
			self.process.stdin.write(request_string)
			status = True

		except ValueError:
			status = False

		return status

	def readChildResponse (self):
		try:
			response = None
			while not response:
				response = self.process.stdout.readline()

		except:
			response = None

		if response:
			response = response.strip()

		return response


	def createChildRequest (self, peer, message, http_header):
		return '%s %s - %s -\n' % (message.url_noport, peer, message.request.method)

	def classifyURL (self, request, url_response):
		if not url_response:
			return 'permit', None, None

		if url_response.startswith('http://'):
			response = url_response[7:]

			if response == request.url_noport:
				return 'permit', None, ''

			if response.startswith(request.host + '/'):
				_, rewrite_path = response.split('/', 1) if '/' in request.url else ''
				return 'rewrite', rewrite_path, ''

		if url_response.startswith('file://'):
			return 'file', url_response[7:], ''

		if url_response.startswith('intercept://'):
			return 'intercept', url_response[12:], ''

		if url_response.startswith('redirect://'):
			return 'redirect', url_response[11:], ''

		return 'file', 'internal_error.html', ''


	def parseHTTP (self, client_id, peer, http_header):
		message = HTTP(self.configuration, http_header, peer)
		message.parse(self._transparent)
		return message

	def validateHTTP (self, client_id, message):
		if message.reply_code:
			try:
				version = message.request.version
			except AttributeError:
				version = '1.0'

			if message.reply_string:
				clean_header = message.raw.replace('\t','\\t').replace('\r','\\r').replace('\n','\\n\n')
				content = '%s<br/>\n<!--\n\n<![CDATA[%s]]>\n\n-->\n' % (message.reply_string, clean_header)
				response = Respond.http(client_id, http(str(message.reply_code), content, version))
			else:
				response = Respond.http(client_id, http(str(message.reply_code),'',version))

		else:
			response = None

		return response

	def doHTTPRequest (self, client_id, peer, message, http_header, source):
		method = message.request.method

		if self.enabled:
			request_string = self.createChildRequest(peer, message, http_header) if message else None
			status = self.writeChild(request_string) if request_string else None

			if status is True:
				response = Respond.defer(client_id, message)

			else:
				response = None

		else:
			response = Respond.download(client_id, message.host, message.port, message.upgrade, message.content_length, message)
			self.usage.logRequest(client_id, peer, method, message.url, 'PERMIT', message.host)

		return response

	def doHTTPConnect (self, client_id, peer, message, http_header, source):
		method = message.request.method

		if not self.configuration.http.allow_connect or message.port not in self.configuration.security.connect:
			# NOTE: we are always returning an HTTP/1.1 response
			response = Respond.http(client_id, http('501', 'CONNECT NOT ALLOWED\n'))
			self.usage.logRequest(client_id, peer, method, message.url, 'DENY', 'CONNECT NOT ALLOWED')

		elif self.enabled:
			request_string = self.createChildRequest(peer, message, http_header) if message else None
			status = self.writeChild(request_string) if request_string else None

			if status is True:
				response = Respond.defer(client_id, message)

			else:
				response = None

		else:
			response = Respond.connect(client_id, message.host, message.port, message)
			self.usage.logRequest(client_id, peer, method, message.url, 'PERMIT', message.host)

		return response

	def doHTTPOptions (self, client_id, peer, message):
		# NOTE: we are always returning an HTTP/1.1 response
		method = message.request.method

		if message.headers.get('max-forwards',''):
			max_forwards = message.headers.get('max-forwards','Max-Forwards: -1')[-1].split(':')[-1].strip()
			max_forward = int(max_forwards) if max_forwards.isdigit() else None

			if max_forward is None:
				response = Respond.http(client_id, http('400', 'INVALID MAX-FORWARDS\n'))
				self.usage.logRequest(client_id, peer, method, message.url, 'ERROR', 'INVALID MAX FORWARDS')

			elif max_forward == 0:
				response = Respond.http(client_id, http('200', ''))
				self.usage.logRequest(client_id, peer, method, message.url, 'PERMIT', method)

			else:
				response = None

			message.headers.set('max-forwards','Max-Forwards: %d' % (max_forward-1))

		if response is None:
			response = Respond.download(client_id, message.headerhost, message.port, message.upgrade, message.content_length, message)

		return response

	def doHTTP (self, client_id, peer, http_header, source):
		message = self.parseHTTP(client_id, peer, http_header)
		response = self.validateHTTP(client_id, message)

		if message is not None:
			message = self.addHeaders(message, peer)
			method = message.request.method

			if method in ('GET', 'PUT', 'POST','HEAD','DELETE','PATCH'):
				response = self.doHTTPRequest(client_id, peer, message, http_header, source)

			elif method == 'CONNECT':
				response = self.doHTTPConnect(client_id, peer, message, http_header, source)

			elif method in ('OPTIONS','TRACE'):
				response = self.doHTTPOptions(client_id, peer, message)

			elif method in (
			'BCOPY', 'BDELETE', 'BMOVE', 'BPROPFIND', 'BPROPPATCH', 'COPY', 'DELETE','LOCK', 'MKCOL', 'MOVE',
			'NOTIFY', 'POLL', 'PROPFIND', 'PROPPATCH', 'SEARCH', 'SUBSCRIBE', 'UNLOCK', 'UNSUBSCRIBE', 'X-MS-ENUMATTS'):
				response = Respond.download(client_id, message.headerhost, message.port, message.upgrade, message.content_length, message)
				self.usage.logRequest(client_id, peer, method, message.url, 'PERMIT', method)

			elif message.request in self.configuration.http.extensions:
				response = Respond.download(client_id, message.headerhost, message.port, message.upgrade, message.content_length, message)
				self.usage.logRequest(client_id, peer, method, message.url, 'PERMIT', message.request)

			else:
				# NOTE: we are always returning an HTTP/1.1 response
				response = Respond.http(client_id, http('405', ''))  # METHOD NOT ALLOWED
				self.usage.logRequest(client_id, peer, method, message.url, 'DENY', method)

		else:
			response = Respond.hangup(client_id)

		return response


	def doMonitor (self, client_id, peer, http_header, source):
		message = self.parseHTTP(client_id, peer, http_header)
		response = self.validateHTTP(client_id, message)  # pylint: disable=W0612

		return Respond.monitor(client_id, message.request.path)


	def decide (self, client_id, peer, header, subheader, source):
		if self.checkChild():
			if source == 'proxy':
				response = self.doHTTP(client_id, peer, header, source)

			elif source == 'web':
				response = self.doMonitor(client_id, peer, header, source)

			else:
				response = Respond.hangup(client_id)

		else:
			response = Respond.error(client_id)

		return response

	def progress (self, client_id, peer, message, http_header, subheader, source):
		if self.checkChild():
			response_s = self.readChildResponse()
			response = self.classifyURL(message.request, response_s) if response_s is not None else None

		else:
			response = None

		if response is not None and source == 'proxy':
			classification, data, comment = response

			if classification == 'requeue':
				(operation, destination) = None, None
				decision = Respond.requeue(client_id, peer, http_header, subheader, source)

			elif message.request.method in ('GET','PUT','POST','HEAD','DELETE','PATCH'):
				(operation, destination), decision = self.response_factory.contentResponse(client_id, message, classification, data, comment)

			elif message.request.method == 'CONNECT':
				(operation, destination), decision = self.response_factory.connectResponse(client_id, message, classification, data, comment)

			else:
				# How did we get here
				operation, destination, decision = None, None, None

			if operation is not None:
				self.usage.logRequest(client_id, peer, message.request.method, message.url, operation, message.host)

		else:
			decision = None

		if decision is None:
			decision = Respond.error(client_id)

		return decision

	def shutdown(self):
		if self.process is not None:
			self.child_factory.destroyProcess(self.process)
			self.process = None
