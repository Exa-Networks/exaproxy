from .messagebox import MessageBox

def cycler():
	def cycle_identifiers():
		while True:
			for identifier in xrange(0xffff):
				yield identifier

	return cycle_identifiers().next



class ControlBox:
	def __init__ (self, channel_in, channel_out):
		self.box = MessageBox(channel_in, channel_out)
		self.next_identifier = cycler()

	def send (self, command, *args):
		identifier = self.next_identifier()
		self.box.put((identifier, command, args))
		return identifier

	def receive (self, identifier=None):
		message = self.box.get()

		if message is not None:
			ack, command, data = message

		else:
			ack, command, data = None, None

		if identifier is not None and ack != identifier:
			data = None

		return command, data

	def wait_stop (self):
		message = self.box.get()

		if message is None:
			return True

		raise RuntimeError, 'got data from a process that should have stopped'


class SlaveBox:
	def __init__ (self, channel_in, channel_out):
		self.box = MessageBox(channel_in, channel_out)

	def receive (self):
		message = self.box.get()

		if message is not None:
			identifier, command, data = message

		else:
			identifier, command, data = None, None, None

		return identifier, command, data

	def respond (self, identifier, command, *args):
		self.box.put((identifier, command, args))
