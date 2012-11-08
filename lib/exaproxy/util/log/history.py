

class History:
	def __init__ (self, count=100):
		self.messages = []
		self.pos = count - 1

	def record (self, level, text, timestamp):
		message = level, text, timestamp
		self.messages = self.messages[-self.pos:] + [message]

	def snapshot (self):
		return self.messages[:]
