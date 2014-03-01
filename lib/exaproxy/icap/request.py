class ICAPRequest(object):
	def __init__ (self, headers, http_request, icap_header, http_header):
		self.headers = headers
		self.http_request = http_request
		self.icap_header = icap_header
		self.http_header = http_header

class ICAPRequestFactory:
	def __init__ (self, configuration):
		self.configuration = configuration

	def create (self, headers, http_request, icap_header, http_header):
		return ICAPRequest(headers, http_request, icap_header, http_header)
