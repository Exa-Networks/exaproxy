

class ICAPResponse (object):
	def __init__ (self, version, code, status, headers, icap_header, http_header, intercept_header=None):
		self.version = version
		self.code = code
		self.status = status
		self.headers = headers
		self.icap_header = icap_header
		self.http_header = http_header
		self.intercept_header = intercept_header

	@property
	def pragma (self):
		return self.headers.get('pragma', {})

	@property
	def is_permit (self):
		return self.code == 304

	@property
	def is_modify (self):
		return self.code == 302 and self.intercept_header is None

	@property
	def is_content (self):
		return self.code == 200

	@property
	def is_intercept (self):
		return self.code == 302 and self.intercept_header is not None
		

class ICAPResponseFactory:
	def __init__ (self, configuration):
		self.configuration = configuration

	def create (self, version, code, status, headers, icap_header, http_header, intercept_header=None):
		return ICAPResponse(version, code, status, headers, icap_header, http_header, intercept_header=intercept_header)
