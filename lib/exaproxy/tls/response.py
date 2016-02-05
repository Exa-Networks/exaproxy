class TLSResponse (object):
	@property
	def is_handshake (self):
		return False

	@property
	def is_failure (self):
		return False



class TLSFailureResponse (TLSResponse):
	def __init__ (self, version, reason):
		self.version = version
		self.reason = reason

	@property
	def is_failure (self):
		return True






TLS_CONTENT_ALERT  = 15
TLS_RESPONSE_FATAL =  2

TLS_FAILURE_HANDSHAKE = 40


class TLSResponseFactory (object):
	version = 3

	def __init__ (self, configuration):
		self.configuration = configuration

	def getHandshakeFailure (self):
		return TLSFailureResponse(self.version, TLS_FAILURE_HANDSHAKE)


	def encodeFailureResponse (reason):
		return '\x15\x03' + chr(self.version) + '\x00\x02\x02' + chr(reason)
