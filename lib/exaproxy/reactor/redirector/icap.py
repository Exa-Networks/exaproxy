# encoding: utf-8
"""
process.py

Created by Thomas Mangin on 2011-11-29.
Copyright (c) 2011-2013  Exa Networks. All rights reserved.
"""

from .response import ResponseEncoder as Respond
from exaproxy.icap.parser import ICAPParser


class ICAPRedirector (Redirector):
	ICAPParser = ICAPParser

	def __init__ (self, configuration, name, request_box, program):
		self.icap_parser = self.ICAPParser(configuration)
		Redirector.__init__ (self, configuration, name, request_box, program)

	def readChildResponse (self):
		try:
			response = self.process.stdout.readline()
			code = (response.rstrip().split()+[None])[1] if response else None
			length = -1

			while True:
				line = self.process.stdout.readline()
				response += line

				if not line:
					response = None
					break

				elif not line.rstrip():
					break

				if line.startswith('Encapsulated: res-hdr=0, null-body='):
					length = int(line.split('=')[-1])

			read_bytes = 0
			bytes_to_read = max(0, length)

			while read_bytes < bytes_to_read:
				headers_s = self.process.stdout.read(bytes_to_read-read_bytes)
				response += headers_s
				read_bytes += len(headers_s)

			if code is None:
				response = None

			# 304 (not modified)
			elif code != '304' and length < 0:
				response = None

		except IOError:
			response = None

		try:
			child_stderr = self.process.stderr.read(4096)
		except Exception, e:
			child_stderr = ''

		if child_stderr:
			response = None

		return response


	def createICAPRequest (self, peer, http_header, icap_header):
		username = icap_header.headers.get('x-authenticated-user', '').strip() if icap_header else None
		groups = icap_header.headers.get('x-authenticated-groups', '').strip() if icap_header else None
		ip_addr = icap_header.headers.get('x-client-ip', '').strip() if icap_header else None
		customer = icap_header.headers.get('x-customer-name', '').strip() if icap_header else None

		icap_request = """\
REQMOD %s ICAP/1.0
Host: %s
Pragma: client=%s
Pragma: host=%s""" % (
			self.protocol, self.icap,
			peer, http_header.host,
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



	def decideICAP (self, response_string):
		return Respond.icap(client_id, response_string) if icap_response else None

	def decideHTTP (self, icap_response):
		# 304 (not modified)
		if icap_response.code == '304':
			return 'permit', None, None

		if icap_response.isContent():
			return 'http', icap_response.http_header, icap_response.comment

		if icap_response.isIntercept():
			return 'intercept', icap_response.destination, icap_response.comment

		return 'permit', None, comment

	def doICAP (self, client_id, peer, icap_header, http_header, tainted):
		icap_request = self.icap_parser.parseRequest(peer, icap_header, http_header)
		http_request = self.http_parser.parseRequest(peer, http_header)

		request_string = self.createICAPRequest(peer, http_request, icap_request) if icap_request else None
		return self.queryChild(request_string) if request_string else None

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
			response = None

		return response

    def progress (self, client_id, peer, request, http_header, subheader, source):
		if self.checkChild():
			response_string = self.readChildResponse()

		else:
			response_string = None

		if response_string is not None and source == 'icap':
			classification = self.decideICAP(response_string)

		elif response_string is not None and source == 'web':
			icap_header, http_header = self.icap_parser.splitResponse(response_string)
			icap_response = self.icap_parser.parseResponse(icap_header, http_header)

			classification = self.decideHTTP(icap_response)

		elif response_string is not None:
			classification = None

		if classification is not None:
			

		return decision

