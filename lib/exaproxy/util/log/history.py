
from collections import deque

class History:
	def __init__ (self, size=1000):
		self.size = size
		self.messages = deque()

	def record (self, level, text, timestamp):
		message = level, text, timestamp
		self.messages.append(message)
		if len(self.messages) > self.size:
			self.messages.popleft()

	def snapshot (self):
		return list(self.messages)
