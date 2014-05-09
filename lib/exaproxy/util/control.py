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

	def receive (self, identifier):
		message = self.box.get()

		if message is not None:
			ack, data = message

		else:
			ack, data = None, None

		if ack != identifier:
			data = None

		return data


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

	def respond (self, identifier, *args):
		self.box.put((identifier, args))
