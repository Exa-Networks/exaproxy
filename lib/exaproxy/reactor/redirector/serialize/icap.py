# encoding: utf-8

class ICAPSerializer (object):
	def __init__ (self, configuration, protocol):
		self.configuration = configuration
		self.protocol = protocol

	def serialize (self, accept_addr, peer, message, icap_message, http_header, path, icap_host):
		if icap_message is not None and icap_message.method == 'OPTIONS':
			res = self.createOptionsRequest(accept_addr, peer, icap_message, path)
			return res

		return self.createRequest(accept_addr, peer, message, icap_message, http_header, path, icap_host)

	def createOptionsRequest (self, accept_addr, peer, icap_message, path):
		return """\
OPTIONS %s ICAP/1.0
Pragma: client=%s

""" % (path, peer)

	def createRequest (self, accept_addr, peer, message, icap_message, http_header, path, icap_host):
		username = icap_message.headers.get('x-authenticated-user', '').strip() if icap_message else None
		groups = icap_message.headers.get('x-authenticated-groups', '').strip() if icap_message else None
		ip_addr = icap_message.headers.get('x-client-ip', '').strip() if icap_message else None
		customer = icap_message.headers.get('x-customer-name', '').strip() if icap_message else None
		allow = icap_message.headers.get('allow', '').strip() if icap_message else None

		icap_request = """\
REQMOD %s ICAP/1.0
Host: %s
Pragma: transport=%s
Pragma: accept=%s
Pragma: client=%s
Pragma: host=%s
Pragma: path=%s
Pragma: method=%s""" % (

			path, icap_host, message.request.protocol,
			accept_addr, peer, message.host, message.request.path, message.request.method,
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

		if allow:
			icap_request += """
Allow: %s""" % allow

		return icap_request + """
Encapsulated: req-hdr=0, null-body=%d

%s""" % (len(http_header), http_header)
