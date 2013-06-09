from collections import deque
import time

class Empty (Exception):
	pass

class Queue():
	def __init__ (self):
		self.queue = deque()

	def qsize (self):
		return len(self.queue)

	def put (self, message):
			self.queue.append(message)

	def get (self, timeout=None):
		try:
			found, res = (True, self.queue.popleft()) if self.queue else (False, None)
		except IndexError:
			found, res = False, None

		if found:
			delay = None
			endtime = None
			remaining = None

		else:
			delay = 0.0005
			endtime = (time.time() + timeout) if timeout is not None else None
			remaining = timeout

		while (remaining is None or remaining > 0) and not found:
			try:
				while not found:
					remaining = (endtime - time.time()) if endtime is not None else None
					if remaining is not None and remaining <= 0:
						break

					delay = min(0.05, 2*delay, remaining)
					time.sleep(delay)

					# try again to read from the queue
					found, res = (True, self.queue.popleft()) if self.queue else (False, None)
			except IndexError:
				pass

		if not found:
			raise Empty

		return res


if __name__ == '__main__':
	q = Queue()
	q.put('foo')
	q.put('bar')
	print q.get(1)
	print q.get(1)
	print q.get(1)
	print q.get(1)
	q.put('yay')
	print q.get(1)
