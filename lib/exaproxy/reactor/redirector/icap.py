# encoding: utf-8
"""
process.py

Created by Thomas Mangin on 2011-11-29.
Copyright (c) 2011-2013  Exa Networks. All rights reserved.
"""

from .response import ResponseEncoder as Respond
from exaproxy.icap.parser import ICAPParser

from .worker import Redirector


class ICAPRedirector (Redirector):
	ICAPParser = ICAPParser

	def __init__ (self, configuration, name, program, protocol):
		self.icap_parser = self.ICAPParser(configuration)
		self.protocol = protocol
		self.icap = protocol[len('icap://'):].split('/')[0]

		Redirector.__init__ (self, configuration, name, program, protocol)

	def readChildResponse (self):
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

			body_string = ''
			bytes_to_read = header.content_length
			read_bytes = 0
			chunked = False

			while bytes_to_read > 0:
				while read_bytes < bytes_to_read:
					headers_s = self.process.stdout.read(bytes_to_read-read_bytes)
					body_string += headers_s
					read_bytes += len(headers_s)

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
				body_string = None

			elif header.code is None:
				header_string = None
				body_string = None

			elif header.code != '304' and bytes_to_read is None:
				header_string = None
				body_string = None

		except IOError, e:
			header_string = None
			body_string = None

		try:
			child_stderr = self.process.stderr.read(4096)
		except Exception:
			child_stderr = ''

		if child_stderr:
			header_string = None
			body_string = None

		if header_string is None:
			return None

		return self.icap_parser.continueResponse(header, body_string)

	def createChildRequest (self, peer, message, http_header):
		return self.createICAPRequest(peer, message, None, http_header)

	def createICAPRequest (self, peer, message, icap_message, http_header):
		username = icap_message.headers.get('x-authenticated-user', '').strip() if icap_message else None
		groups = icap_message.headers.get('x-authenticated-groups', '').strip() if icap_message else None
		ip_addr = icap_message.headers.get('x-client-ip', '').strip() if icap_message else None
		customer = icap_message.headers.get('x-customer-name', '').strip() if icap_message else None

		icap_request = """\
REQMOD %s ICAP/1.0
Host: %s
Pragma: transport=%s
Pragma: client=%s
Pragma: host=%s
Pragma: path=%s
Pragma: method=%s""" % (

			self.protocol, self.icap, message.request.protocol,
			peer, message.host, message.request.path, message.request.method,
			)

		if ip_addr:
			icap_request += """
X-Client-IP: %s""" % ip_addr

		if username:
			icap_request += """
X-Authenticated-User: %s""" % username

		if groups:
			icap_request += """
X-Authenticated-Groups: %s""" % groups

		if customer:
			icap_request += """
X-Customer-Name: %s""" % customer

		return icap_request + """
Encapsulated: req-hdr=0, null-body=%d

%s""" % (len(http_header), http_header)



	def decideICAP (self, client_id, icap_response, message):
		if message.complete:
			length = max(0, message.content_length - len(message.http_header))

		else:
			length = 'chunked'

		return Respond.icap(client_id, icap_response, length) if icap_response else None

	def decideHTTP (self, client_id, icap_response, message, peer, source):
		# 304 (not modified)
		if icap_response.is_permit:
			classification, data, comment = 'permit', None, None

		elif icap_response.is_modify:
			message = self.parseHTTP(client_id, peer, icap_response.http_header)
			if message.validated:
				classification, data, comment = 'permit', None, None

			else:
				classification, data, comment = None, None, None

		elif icap_response.is_content:
			classification, data, comment = 'http', icap_response.http_header, icap_response.pragma.get('comment', '')

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


	def doICAP (self, client_id, peer, icap_header, http_header):
		icap_request = self.icap_parser.parseRequest(icap_header, http_header)
		http_request = self.http_parser.parseRequest(peer, http_header)

		request_string = self.createICAPRequest(peer, http_request, icap_request, http_header) if icap_request else None
		status = self.writeChild(request_string) if request_string else None

		return Respond.defer(client_id, icap_request) if status else None

	def decide (self, client_id, peer, header, subheader, source):
		if self.checkChild():
			if source == 'icap':
				response = self.doICAP(client_id, peer, header, subheader)

			elif source == 'proxy':
				response = self.doHTTP(client_id, peer, header, source)

			elif source == 'web':
				response = self.doMonitor(client_id, peer, header, source)

			else:
				response = Respond.hangup(client_id)

		else:
			response = Respond.error(client_id)

		return response

	def progress (self, client_id, peer, message, icap_header, http_header, source):
		if self.checkChild():
			icap_response = self.readChildResponse()

		else:
			icap_response = None

		if icap_response:
			if source == 'icap':
				return self.decideICAP(client_id, icap_response.response_string, message)

			if source == 'proxy':
				return self.decideHTTP(client_id, icap_response, message, peer, source)

			return Respond.hangup(client_id)

		# Something bad happened...
		return Respond.error(client_id)
