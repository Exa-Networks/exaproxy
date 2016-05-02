# encoding: utf-8



class TLSSerializer (object):
	def __init__ (self, configuration, protocol):
		self.configuration = configuration
		self.protocol = protocol

	def serialize (self, accept_addr, peer, message, tls_header, path, icap_host):
		icap_request = """\
REQMOD %s ICAP/1.0
Host: %s
Pragma: transport=%s
Pragma: accept=%s
Pragma: client=%s
Pragma: host=%s
Pragma: path=%s
Pragma: method=%s""" % (

			path, icap_host, 'tls',
			peer, accept_addr, message.hostname, '', 'TLS',
			)

		return icap_request + """
Encapsulated: req-hdr=0, null-body=%d

%s""" % (len(tls_header), tls_header)
