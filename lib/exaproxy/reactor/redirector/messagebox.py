import os
import signal

from exaproxy.util.messagebox import MessageBox, MessageReader


class ProxyToRedirectorMessageBox:
	def __init__ (self, pid, pipe_in, pipe_out):
		self.pid = pid
		self.box = MessageBox(pipe_in, pipe_out)

	def close (self):
		return self.box.close()

	def sendRequest (self, client_id, peer, request, subrequest, source):
		message = client_id, peer, request, subrequest, source
		return self.box.put(message)

	def getDecision (self):
		message = self.box.get()
		if message is not None:
			client_id, command, decision = message

		else:
			client_id, command, decision = None, None, None

		return client_id, command, decision

	def stop (self):
		os.kill(self.pid, signal.SIGSTOP)

	def respawn (self):
		os.kill(self.pid, signal.SIGHUP)

	def decreaseSpawnCount (self, count=1):
		for _ in range(count):
			os.kill(self.pid, signal.SIGUSR1)

	def increaseSpawnCount (self, count=1):
		for _ in range(count):
			os.kill(self.pid, signal.SIIGUSR2)


class RedirectorToProxyMessageBox:
	def __init__ (self, pipe_in, pipe_out):
		self.box = MessageBox(pipe_in, pipe_out)

	def close (self):
		return self.box.close()

	def isClosed (self):
		return self.box.pipe_in.closed

	def getRequest (self):
		return self.box.get()

	def sendResponse (self, client_id, command, decision):
		message = client_id, command, decision
		return self.box.put(message)




class RedirectorMessageBox:
	def __init__ (self, pipe_in, pipe_out):
		self.box = MessageBox(pipe_in, pipe_out)

	def close (self):
		return self.box.close()

	def getResponse (self):
		return self.box.get()

	def sendResponse (self, message):
		return self.box.put(message)


class RedirectorMessageReader:
	def __init__ (self):
		self.box = MessageReader()

	def getResponse (self, pipe_in):
		return self.box.get(pipe_in)
