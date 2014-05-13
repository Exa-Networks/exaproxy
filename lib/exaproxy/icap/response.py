
class ICAPResponse (object):
	def __init__ (self, version, code, status, headers, icap_header, http_header):
		self.version = version
		self.code = code
		self.status = status
		self.headers = headers
		self.icap_header = icap_header
		self.http_header = http_header

	@property
	def pragma (self):
		return self.headers.get('pragma', {})

	@property
	def is_permit (self):
		return False

	@property
	def is_modify (self):
		return False

	@property
	def is_content (self):
		return False

	@property
	def is_intercept (self):
		return False


class ICAPRequestModification (ICAPResponse):
	def __init__ (self, version, code, status, headers, icap_header, http_header, intercept_header=None):
		ICAPResponse.__init__(self, version, code, status, headers, icap_header, http_header)
		self.intercept_header = intercept_header

	@property
	def is_permit (self):
		return self.code == 304

	@property
	def is_modify (self):
		return self.code == 200 and self.intercept_header is None

	@property
	def is_intercept (self):
		return self.code == 200 and self.intercept_header is not None


class ICAPResponseModification (ICAPResponse):
	@property
	def is_content (self):
		return self.code == 200


class ICAPResponseFactory:
	def __init__ (self, configuration):
		self.configuration = configuration

	def create (self, version, code, status, headers, icap_header, request_header, response_header, intercept_header=None):
		if response_header:
			response = ICAPResponseModification(version, code, status, headers, icap_header, response_header)

		else:
			response = ICAPRequestModification(version, code, status, headers, icap_header, request_header, intercept_header=intercept_header)

		return response
