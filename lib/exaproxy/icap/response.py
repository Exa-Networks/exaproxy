

class ICAPResponse (object):
	def __init__ (self, version, code, status, headers, icap_header, http_header):
		self.version = version
		self.code = code
		self.status = status
		self.headers = headers
		self.icap_header = icap_header
		self.http_header = http_header

	def isIntercept (self):
		connect = self.http_headers.startswith('CONNECT')
		if connect:
			

class ICAPRequestFactory:
	def __init__ (self, configuration):
		self.configuration = configuration

	def create (self, version, code, status, headers, icap_header, http_header):
		return ICAPRequest(version, code, status, headers, icap_header, http_header)
