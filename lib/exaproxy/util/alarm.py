import os
from threading import Thread

from .messagequeue import Queue, Empty
from .messagebox import MessageBox

class AlarmThread (Thread):
	def __init__ (self, messagebox, queue, period):
		self.messagebox = messagebox
		self.queue = queue
		self.period = period
		Thread.__init__(self)

	def run (self):
		while True:
			command, message = self.queue.get()

			while True:
				if command == 'STOP':
					break

				if command == 'ALARM':
					try:
						command, message = self.queue.get(timeout=self.period)

					except Empty: pass

					else:
						continue

					self.messagebox.put('alarm')


			if command == 'STOP':
				break


class AlarmDispatcher (object):
	dispatcher_factory = AlarmThread

	def __init__ (self, messagebox, period):
		self.messagebox = messagebox
		self.queue = Queue()
		self.thread = self.dispatcher_factory(messagebox, self.queue, period)

	def start (self):
		self.thread.start()

	def stop (self):
		self.queue.put(('STOP', ''))
		self.thread.join()
		return True

	def setAlarm (self):
		# NOTE: could dynamically set the delay by passing it through the pipe
		self.queue.put(('ALARM', ''))

	def acknowledgeAlarm (self):
		return self.messagebox.get()




def alarm_thread (poller, period):
	r, w = os.pipe()
	message_box = MessageBox(r, w)

	dispatcher = AlarmDispatcher(message_box, period)
	dispatcher.start()

	poller.addReadSocket('read_interrupt', dispatcher.messagebox.pipe_in)
	return dispatcher
