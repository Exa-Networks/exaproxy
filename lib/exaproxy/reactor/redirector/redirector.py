from .worker import Redirector
from .icap import ICAPRedirector

class RedirectorFactory (object):
	def __init__ (self, configuration, program, protocol):
		self.configuration = configuration
		self.program = program
		self.protocol = protocol

	def create (self, wid):
		if self.protocol == 'url':
			redirector = Redirector(self.configuration, wid, self.program, self.protocol)

		elif self.protocol.startswith('icap://'):
			redirector = ICAPRedirector(self.configuration, wid, self.program, self.protocol)

		else:
			redirector = None

		return redirector
