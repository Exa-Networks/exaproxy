# encoding: utf-8



class PassthroughSerializer (object):
	def __init__ (self, configuration, protocol):
		self.configuration = configuration
		self.protocol = protocol

	def serialize (self, accept_addr, accept_port, peer, path, icap_host):
		icap_request = """\
REQMOD %s ICAP/1.0
Host: %s
Pragma: transport=%s
Pragma: accept=%s
Pragma: accept-port=%s
Pragma: client=%s
Pragma: method=%s""" % (

			path, icap_host, 'tcp',
			accept_addr, accept_port, peer, 'TCP',
			)

		return icap_request + """
Encapsulated: req-hdr=0, null-body=0

"""
