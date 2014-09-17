from collections import OrderedDict

class ICAPRequest(object):
	__slots__ = ('method', 'url', 'version', 'headers', 'icap_header', 'http_header', 'offsets', 'content_length', 'complete')

	def __init__ (self, method, url, version, headers, icap_header, http_header, offsets, content_length, complete):
		self.method = method
		self.url = url
		self.version = version
		self.headers = headers
		self.icap_header = icap_header
		self.http_header = http_header
		self.offsets = OrderedDict(offsets)
		self.content_length = content_length
		self.complete = complete

	@property
	def contains_headers (self):
		return 'req-hdr' in self.offsets and self.content_length > 0

	@property
	def contains_body (self):
		return 'req-body' in self.offsets


class ICAPRequestFactory:
	def __init__ (self, configuration):
		self.configuration = configuration

	def create (self, method, url, version, headers, icap_header, http_header, offsets, content_length, complete):
		return ICAPRequest(method, url, version, headers, icap_header, http_header, offsets, content_length, complete)
