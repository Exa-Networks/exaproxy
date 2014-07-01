from threading import Thread
from exaproxy.util.messagequeue import Queue


class DispatcherThread (Thread):
	def __init__ (self, messagebox, queue):
		self.messagebox = messagebox
		self.queue = queue
		Thread.__init__(self)

	def run (self):
		while True:
			command, message = self.queue.get()

			if command == 'REQUEST':
				self.messagebox.box.put(message)
				continue

			if command == 'STOP':
				break


class RedirectorDispatcher (object):
	dispatcher_factory = DispatcherThread

	def __init__ (self, messagebox):
		self.messagebox = messagebox
		self.queue = Queue()
		self.thread = self.dispatcher_factory(messagebox, self.queue)

	def start (self):
		self.thread.start()

	def stop (self):
		self.queue.put(('STOP', ''))
		self.thread.join()
		return self.messagebox.stop()

	def sendRequest (self, client_id, peer, request, subrequest, source):
		message = client_id, peer, request, subrequest, source
		return self.queue.put(('REQUEST', message))

	def getDecision (self):
		return self.messagebox.getDecision()

	def respawn (self):
		return self.messagebox.respawn()

	def decreaseSpawnLimit (self, *args):
		return self.messagebox.decreaseSpawnLimit(*args)

	def increaseSpawnLimit (self, *args):
		return self.messagebox.increaseSpawnLimit(*args)

	def getStats (self):
		return self.messagebox.getStats()
