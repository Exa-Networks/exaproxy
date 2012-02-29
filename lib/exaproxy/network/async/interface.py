# encoding: utf-8
"""
poller.py

Created by David Farrar on 2012-01-31.
Copyright (c) 2011 Exa Networks. All rights reserved.
"""

class IPoller:
	"""Interface for pollers"""

	def addReadSocket(self, name, socket):
		"""Start watching for data in the socket's recvbuf"""
		raise NotImplementedError

	def removeReadSocket(self, name, socket):
		"""Stop watching the socket for incoming data"""
		raise NotImplementedError

	def corkReadSocket(self, name, socket):
		"""Stop watching the socket for incoming data. The socket is
		   still in use at this point and we expect this operation to
		   be reversed so don't clean up data we will need again"""
		raise NotImplementedError

	def uncorkReadSocket(self, name, socket):
		"""Start watching the socket for incoming data again"""
		raise NotImplementedError

	def setupRead(self, name):
		"""Define a new event that sockets can subscribe to"""
		raise NotImplementedError

	def clearRead(self, name):
		"""Flush all sockets currently watched for the event"""
		raise NotImplementedError

	def addWriteSocket(self, name, socket):
		"""Start watching for space in the socket's sendbuf"""
		raise NotImplementedError

	def removeWriteSocket(self, name, socket):
		"""Stop watching for space in the socket's sendbuf"""
		raise NotImplementedError

	def corkWriteSocket(self, name, socket):
		"""Stop waiting for space in the socket's sendbuf. The socket is
		   still in use at this point and we expect this operation to
		   be reversed so don't clean up data we will need again"""
		raise NotImplementedError

	def uncorkWriteSocket(self, name, socket):
		"""Start watching for space in the socket's sendbuf again"""
		raise NotImplementedError

	def setupWrite(self, name):
		"""Define a new event that sockets can subscribe to"""
		raise NotImplementedError

	def clearWrite(self, name):
		"""Flush all sockets currently watched for the event"""
		raise NotImplementedError

	def poll(self):
		"""Wait for events we're watching for to occur and
		   return a list of each eventful socket per event"""
		raise NotImplementedError
