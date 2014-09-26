class ICAPResponseHeader (object):
	__slots__ = ['info', 'version', 'code', 'status', 'headers', 'header_string', 'offsets', 'content_length', 'body_complete']

	def __init__ (self, version, code, status, headers, header_string, offsets, content_length, body_complete):
		self.info = version, code, status
		self.version = version
		self.code = code
		self.status = status
		self.headers = headers
		self.header_string = header_string
		self.offsets = offsets
		self.content_length = content_length
		self.body_complete = body_complete



class ICAPResponseHeaderFactory (object):
	def __init__ (self, configuration):
		self.configuration = configuration

	def create (self, version, code, status, headers, header_string, offsets, content_length, body_complete):
		return ICAPResponseHeader(version, code, status, headers, header_string, offsets, content_length, body_complete)
