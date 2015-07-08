
class ICAPResponse (object):
	def __init__ (self, version, code, status, headers, icap_header, http_header, http_body):
		self.version = version
		self.code = code
		self.status = status
		self.headers = headers

		icap_len = len(icap_header)
		http_len = len(http_header)
		
		icap_end = icap_len

		if http_header:
			http_string = http_header

			if http_body:
				http_len_string = '%x\n' % len(http_body)
				http_string += http_len_string + http_body + '0\n'

			else:
				http_len_string = ''

			http_header_offset = icap_end
			http_header_end = http_header_offset + len(http_header)

			http_body_offset = http_header_end + len(http_len_string)
			http_body_end = http_body_offset + len(http_body)

		else:
			http_string = http_header
			http_header_offset = icap_end
			http_header_end = icap_end
			http_body_offset = icap_end
			http_body_end = icap_end

		self.response_view = memoryview(icap_header + http_string + '\r\n')
		self.icap_view = self.response_view[:icap_end]
		self.http_header_view = self.response_view[http_header_offset:http_header_end]
		self.http_body_view = self.response_view[http_body_offset:http_body_end]

	@property
	def response_string (self):
		return self.response_view.tobytes()

	@property
	def icap_header (self):
		return self.icap_view.tobytes()

	@property
	def http_response (self):
		return self.http_header_view.tobytes() + self.http_body_view.tobytes()

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
	def __init__ (self, version, code, status, headers, icap_header, http_header, http_body, intercept_header=None):
		ICAPResponse.__init__(self, version, code, status, headers, icap_header, http_header, http_body)
		self.intercept_header = intercept_header

	@property
	def is_permit (self):
		return self.code == 204

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

	def create (self, version, code, status, headers, icap_header, request_header, response_header, body_string, intercept_header=None):
		if response_header:
			response = ICAPResponseModification(version, code, status, headers, icap_header, response_header, body_string)

		else:
			response = ICAPRequestModification(version, code, status, headers, icap_header, request_header, body_string, intercept_header=intercept_header)

		return response
