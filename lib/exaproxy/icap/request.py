class ICAPRequest(object):
	def __init__ (self, headers, icap_header, http_header):
		self.headers = headers
		self.icap_header = icap_header
		self.http_header = http_header

class ICAPRequestFactory:
	def __init__ (self, configuration):
		self.configuration = configuration

	def create (self, headers, icap_header, http_header):
		return ICAPRequest(headers, icap_header, http_header)
