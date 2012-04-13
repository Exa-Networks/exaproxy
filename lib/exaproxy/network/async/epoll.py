# encoding: utf-8
"""
poller.py

Created by Thomas Mangin on 2011-11-30.
Copyright (c) 2011 Exa Networks. All rights reserved.
"""

# http://scotdoyle.com/python-epoll-howto.html

import select
import errno

from interface import IPoller

from select import EPOLLIN, EPOLLOUT, EPOLLHUP


class EPoller (IPoller):
	epoll = staticmethod(select.epoll)

	def __init__(self, speed):
		self.speed = speed

		self.sockets = {}
		self.pollers = {}
		self.master = self.epoll()
		self.errors = {}


	def addReadSocket(self, name, socket):
		sockets, poller, fdtosock, corked = self.sockets[name]
		if socket not in sockets:
			fileno = socket.fileno()
			sockets.append(socket)
			try:
				poller.register(socket, EPOLLIN | EPOLLHUP)
				res = True
			except socket.error, e:
				sockets.remove(socket)
				res = False
				print "ERROR registering socket (%s): %s" % (str(socket), str(e))

				if socket not in self.errors:
					self.errors[socket] = name
				else:
					print "NOTE: trying to poll closed socket again (addReadSocket)"
					
			else:
				fdtosock[fileno] = socket
		else:
			res = False

		return res

	def removeReadSocket(self, name, socket):
		sockets, poller, fdtosock, corked = self.sockets[name]
		if socket in sockets:
			fdtosock.pop(socket.fileno(), None)
			sockets.remove(socket)
			if socket not in corked:
				poller.unregister(socket)
			else:
				corked.pop(socket)

		if socket in self.errors:
			self.errors.pop(socket)

	def removeClosedReadSocket(self, name, socket):
		pass

	def corkReadSocket(self, name, socket):
		sockets, poller, fdtosock, corked = self.sockets[name]
		if socket in sockets and socket not in corked:
			corked[socket] = True
			poller.unregister(socket)
			res = True
		else:
			res = False

		return res

	def uncorkReadSocket(self, name, socket):
		sockets, poller, fdtosock, corked = self.sockets[name]
		if socket in sockets:
			if corked.pop(socket, None):
				try:
					poller.register(socket, EPOLLIN | EPOLLHUP)
					res = True
				except socket.error, e:
					sockets.remove(socket)
					res = False
					print "ERROR reregistering socket (%s): %s" % (str(socket), str(e))

					if socket not in self.errors:
						self.errors[socket] = name
					else:
						print "NOTE: trying to poll closed socket again (uncorkReadSocket)"
			else:
				res = False
		else:
			res = False

		return res

	def setupRead(self, name):
		if name not in self.sockets:
			poller = self.epoll()
			sockets = []
			fdtosock = {}
			corked = {}
			self.pollers[poller.fileno()] = name, poller, sockets, fdtosock

			self.sockets[name] = sockets, poller, fdtosock, corked
			self.master.register(poller, EPOLLIN)

	def clearRead(self, name):
		sockets, poller, fdtosock, corked = self.sockets.pop(name, ([], None, None, None))
		if sockets:
			self.master.unregister(poller)
			self.pollers.pop(poller.fileno(), None)
			poller.close()
			self.setupRead(name)


	def addWriteSocket(self, name, socket):
		sockets, poller, fdtosock, corked = self.sockets[name]
		if socket not in sockets:
			fileno = socket.fileno()
			sockets.append(socket)
			try:
				poller.register(socket, EPOLLOUT | EPOLLHUP)
				res = True
			except socket.error, e:
				sockets.remove(socket)
				res = False
				print "ERROR registering socket (%s): %s" % (str(socket), str(e))

				if socket not in self.errors:
					self.errors[socket] = name
				else:
					print "NOTE: trying to poll closed socket again (addWriteSocket)"
			else:
				fdtosock[fileno] = socket
		else:
			res = False

		return res

	def removeWriteSocket(self, name, socket):
		sockets, poller, fdtosock, corked = self.sockets[name]
		if socket in sockets:
			fdtosock.pop(socket.fileno(), None)
			sockets.remove(socket)
			if socket not in corked:
				poller.unregister(socket)
			else:
				corked.pop(socket)

		if socket in self.errors:
			self.errors.pop(socket, None)

	def removeClosedWriteSocket(self, name, socket):
		pass

	def corkWriteSocket(self, name, socket):
		sockets, poller, fdtosock, corked = self.sockets[name]
		if socket in sockets and socket not in corked:
			poller.unregister(socket)
			corked[socket] = True
			res = True
		else:
			res = False

		return res

	def uncorkWriteSocket(self, name, socket):
		sockets, poller, fdtosock, corked = self.sockets[name]
		if socket in sockets:
			if corked.pop(socket, None):
				try:
					poller.register(socket, EPOLLOUT | EPOLLHUP)
					res = True
				except socket.error, e:
					sockets.remove(socket)
					res = False
					print "ERROR reregistering socket (%s): %s" % (str(socket), str(e))

					if socket not in self.errors:
						self.errors[socket] = name
					else:
						print "NOTE: trying to poll closed socket again (uncorkWriteSocket)"
			else:
				res = False
		else:
			res = False

		return res

	def setupWrite(self, name):
		if name not in self.sockets:
			poller = self.epoll()
			sockets = []
			fdtosock = {}
			corked = {}
			self.pollers[poller.fileno()] = name, poller, sockets, fdtosock

			self.sockets[name] = sockets, poller, fdtosock, corked
			self.master.register(poller, EPOLLIN)

	def clearWrite(self, name):
		sockets, poller, fdtosock, corked = self.sockets.pop(name, ([], None, None, None))
		if sockets:
			self.master.unregister(poller)
			self.pollers.pop(poller.fileno(), None)
			poller.close()
			self.setupWrite(name)


	def poll(self):
		try:
			res = self.master.poll(self.speed)
		except IOError, e:
			if e.errno != errno.EINTR:
				raise

			res = []
			response = {}
		else:
			response = dict((name, []) for (name, poller, sockets, fdtosock) in self.pollers.values())

		for fd, events in res:
			name, poller, sockets, fdtosock = self.pollers[fd]
			events = poller.poll(0)

			response[name] = [fdtosock[sock_fd] for (sock_fd, sock_events) in events]

		for fd, name in self.errors.itervalues():
			response.setdefault(name, []).append(fd)

#			for sock_fd, sock_events in events:
#				if sock_events & select.EPOLLHUP:
#					print "REMOVING SOCKET BECAUSE WE WERE TOLD IT CLOSED", sock_fd
#					socket = fdtosock.pop(sock_fd, None)
#					poller.unregister(sock_fd)
#					sockets.remove(socket)

		return response
