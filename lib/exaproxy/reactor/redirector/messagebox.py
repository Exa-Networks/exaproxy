# encoding: utf-8
"""
messagebox.py

Created by David Farrar on 2014-06-10 (or earlier).
Copyright (c) 2011-2013  Exa Networks. All rights reserved.
"""

from exaproxy.util.messagebox import MessageBox
from exaproxy.util.control import ControlBox

class ProxyToRedirectorMessageBox:
	def __init__ (self, pid, pipe_in, pipe_out, control_in, control_out):
		self.pid = pid
		self.box = MessageBox(pipe_in, pipe_out)
		self.control = ControlBox(control_in, control_out)

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
		self.control.send('STOP')
		return self.control.wait_stop()

	def respawn (self):
		self.control.send('RESPAWN')

	def decreaseSpawnLimit (self, count=1):
		self.control.send('DECREASE', count)

	def increaseSpawnLimit (self, count=1):
		self.control.send('INCREASE', count)

	def getStats (self):
		identifier = self.control.send('STATS')
		return self.control.receive(identifier)



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
