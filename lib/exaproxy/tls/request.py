# encoding: utf-8

class TLSRequest(object):
	__slots__ = ('hostname',)

	def __init__ (self, hostname):
		self.hostname = hostname


class TLSRequestFactory:
	def __init__ (self, configuration):
		self.configuration = configuration

	def createClientHello (self, hostname):
		return TLSRequest(hostname)
