

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

	def isContent (self):
		return bool(self.http_header) and self.intercept_header is None

	def isIntercept (self):
		return bool(self.intercept_header is not None)
		

class ICAPResponseFactory:
	def __init__ (self, configuration):
		self.configuration = configuration

	def create (self, version, code, status, headers, icap_header, http_header, intercept_header=None):
		return ICAPResponse(version, code, status, headers, icap_header, http_header, intercept_header=intercept_header)
