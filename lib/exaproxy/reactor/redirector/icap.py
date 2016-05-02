# encoding: utf-8
"""
process.py

Created by Thomas Mangin on 2011-11-29.
Copyright (c) 2011-2013  Exa Networks. All rights reserved.
"""

from .serialize.icap import ICAPSerializer
from .serialize.tls import TLSSerializer
from .response import ResponseEncoder as Respond

from exaproxy.icap.parser import ICAPParser
from exaproxy.tls.parser import TLSParser

from .worker import Redirector


class ICAPRedirector (Redirector):
	ICAPParser = ICAPParser
	TLSParser = TLSParser
	ICAPSerializer = ICAPSerializer
	TLSSerializer = TLSSerializer

	def __init__ (self, configuration, name, program, protocol):
		self.icap_parser = self.ICAPParser(configuration)
		self.tls_parser = self.TLSParser(configuration)
		self.icap_serializer = self.ICAPSerializer(configuration, protocol)
		self.tls_serializer = self.TLSSerializer(configuration, protocol)

		self.protocol = protocol
		self.icap = protocol[len('icap://'):].split('/')[0]

		Redirector.__init__ (self, configuration, name, program, protocol)

	def readChildResponse (self):
		header = None
		try:
			header_string = self.process.stdout.readline()
			while True:
				line = self.process.stdout.readline()
				header_string += line

				if not line:
					header_string = None
					break

				elif not line.rstrip():
					break


			header = self.icap_parser.parseResponseHeader(header_string)

			content_s = ''
			bytes_to_read = header.content_length
			read_bytes = 0
			chunked = False

			while bytes_to_read > 0:
				while read_bytes < bytes_to_read:
					chomp_s = self.process.stdout.read(bytes_to_read-read_bytes)
					content_s += chomp_s
					read_bytes += len(chomp_s)

				if header.body_complete:
					bytes_to_read = 0
					break

				if chunked:
					ignore = self.process.stdout.readline()

				line = self.process.stdout.readline()
				bytes_to_read = int(line.strip(), 16)
				chunked = True
				read_bytes = 0

			if bytes_to_read != 0:
				header_string = None
				content_s = None

			elif header.code is None:
				header_string = None
				content_s = None

			elif header.code != '204' and bytes_to_read is None:
				header_string = None
				content_s = None

		except IOError, e:
			header_string = None
			content_s = None

		try:
			child_stderr = self.process.stderr.read(4096)
		except Exception:
			child_stderr = ''

		if child_stderr:
			header_string = None
			content_s = None

		if header_string is None:
			return None

		return self.icap_parser.continueResponse(header, content_s)

	def createChildRequest (self, accept_addr, peer, message, http_header):
		return self.icap_serializer.serialize(accept_addr, peer, message, None, http_header, self.protocol, self.icap)

	def createICAPRequest (self, accept_addr, peer, message, icap_message, http_header):
		return self.icap_serializer.serialize(accept_addr, peer, message, icap_message, http_header, self.protocol, self.icap)

	def createTLSRequest (self, accept_addr, peer, message, tls_header):
		return self.tls_serializer.serialize(accept_addr, peer, message, tls_header, self.protocol, self.icap)

	def decideICAP (self, client_id, icap_response, message):
		if message.complete:
			length = max(0, message.content_length - len(message.http_header))

		else:
			length = 'chunked'

		return Respond.icap(client_id, icap_response, length) if icap_response else None

	def decideTLS (self, client_id, icap_response, message, tls_header, peer):
		if icap_response.is_intercept:
			intercept_request = self.http_parser.parseRequest(peer, icap_response.intercept_header)
			return Respond.intercept(client_id, intercept_request.hostname, intercept_request.port, tls_header)

		if icap_response.is_permit:
			return Respond.intercept(client_id, message.hostname, 443, tls_header)

		# XXX: respond with a TLS error
		return Respond.close(client_id)

	def decideHTTP (self, client_id, icap_response, message, accept_addr, peer, source):
		# 204 (not modified)
		if icap_response.is_permit:
			classification, data, comment = 'permit', None, None

		elif icap_response.is_modify:
			message = self.parseHTTP(client_id, accept_addr, peer, icap_response.http_response)
			if message.validated:
				classification, data, comment = 'permit', None, None

			else:
				classification, data, comment = None, None, None

		elif icap_response.is_content:
			classification, data, comment = 'http', icap_response.http_response, icap_response.pragma.get('comment', '')

		elif icap_response.is_intercept:
			intercept_request = self.http_parser.parseRequest(peer, icap_response.intercept_header)

			if intercept_request:
				destination = intercept_request.host + ':' + str(intercept_request.port)
				classification, data, comment = 'intercept', destination, icap_response.pragma.get('comment', '')

			else:
				classification, data, comment = 'error', None, None

		else:
			classification, data, comment = 'permit', None, None

		if classification is None:
			response = self.validateHTTP(client_id, message)
			if response:
				classification, data, comment = response

			else:
				classification, data, comment = 'error', None, None

		if message.request.method in ('GET','PUT','POST','HEAD','DELETE','PATCH'):
			(operation, destination), decision = self.response_factory.contentResponse(client_id, message, classification, data, comment)

		elif message.request.method == 'CONNECT':
			(operation, destination), decision = self.response_factory.connectResponse(client_id, message, classification, data, comment)

		else:
			# How did we get here
			operation, destination, decision = None, None, None

		return decision


	def doICAP (self, client_id, accept_addr, peer, icap_header, http_header):
		icap_request = self.icap_parser.parseRequest(icap_header, http_header)
		http_request = self.http_parser.parseRequest(peer, http_header) if http_header else None

		request_string = self.createICAPRequest(accept_addr, peer, http_request, icap_request, http_header) if icap_request else None
		status = self.writeChild(request_string) if request_string else None

		return Respond.defer(client_id, icap_request) if status else None

	def doTLS (self, client_id, accept_addr, peer, tls_header, source):
		tls_hello = self.tls_parser.parseClientHello(tls_header)
		request_string = self.createTLSRequest(accept_addr, peer, tls_hello, tls_header) if tls_hello else None
		status = self.writeChild(request_string) if request_string else None

		return Respond.defer(client_id, tls_hello) if status else None

	def decide (self, client_id, accept_addr, peer, header, subheader, source):
		if self.checkChild():
			if source == 'icap':
				response = self.doICAP(client_id, accept_addr, peer, header, subheader)

			elif source == 'proxy':
				response = self.doHTTP(client_id, accept_addr, peer, header, source)

			elif source == 'web':
				response = self.doMonitor(client_id, accept_addr, peer, header, source)

			elif source == 'tls':
				response = self.doTLS(client_id, accept_addr, peer, header, source)

			else:
				response = Respond.hangup(client_id)

		else:
			response = Respond.error(client_id)

		return response

	def progress (self, client_id, accept_addr, peer, message, header, sub_header, source):
		if self.checkChild():
			icap_response = self.readChildResponse()

		else:
			icap_response = None

		if icap_response:
			if source == 'icap':
				return self.decideICAP(client_id, icap_response.response_string, message)

			if source == 'proxy':
				return self.decideHTTP(client_id, icap_response, message, accept_addr, peer, source)

			if source == 'tls':
				res = self.decideTLS(client_id, icap_response, message, header, peer)
				return res

			return Respond.hangup(client_id)

		# Something bad happened...
		return Respond.error(client_id)
