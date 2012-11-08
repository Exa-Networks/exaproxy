class MessageStore:
	def __init__ (self):
		self.queue = []

	def addMessage (self, message):
		return self.queue.append(message)

	def readMessages (self):
		self.queue, messages = [], self.queue
		return messages


message_store = MessageStore()
