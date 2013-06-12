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
			if self.queue:
				return self.queue.popleft()
		except IndexError:
			pass

		delay = 0.0005
		start = time.time()

		running = True

		while running:
			try:
				while True:
					if timeout:
						if time.time() > start + timeout:
							running = False
							break

					delay = min(0.05, 2*delay)
					time.sleep(delay)

					if self.queue:
						return self.queue.popleft()
			except IndexError:
				pass

		raise Empty


if __name__ == '__main__':
	q = Queue()
	q.put('foo')
	q.put('bar')
	print q.get(1)
	print q.get(1)
	try:
		q.put('yay')
		print q.get(1)
		print q.get(2)
	except:
		print 'forever - print ^C'
		print q.get()
