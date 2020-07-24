# encoding: utf-8
"""
poller.py

Created by Thomas Mangin on 2011-11-30.
Copyright (c) 2011-2013  Exa Networks. All rights reserved.
"""

# http://scotdoyle.com/python-epoll-howto.html

import select
import errno
import socket

from interface import IPoller

from select import EPOLLIN, EPOLLOUT, EPOLLHUP


class EPoller (IPoller):
	epoll = staticmethod(select.epoll)

	def __init__(self, speed):
		self.speed = speed

		self.sockets = {}
		self.pollers = {}
		self.main = self.epoll()
		self.errors = {}


	def addReadSocket(self, name, sock):
		sockets, poller, fdtosock, corked = self.sockets[name]
		if sock not in sockets:
			sockets[sock] = True
			try:
				fileno = sock.fileno()
				poller.register(sock, EPOLLIN | EPOLLHUP)
				res = True
			except socket.error, e:
				sockets.pop(sock)
				res = False
				print "ERROR registering socket (%s): %s" % (str(sock), str(e))

				if sock not in self.errors:
					self.errors[sock] = name
				else:
					print "NOTE: trying to poll closed socket again (addReadSocket)"

			else:
				fdtosock[fileno] = sock
		else:
			res = False

		return res

	def removeReadSocket(self, name, sock):
		sockets, poller, fdtosock, corked = self.sockets[name]
		if sock in sockets:
			try:
				fdtosock.pop(sock.fileno(), None)
			except socket.error:
				pass

			sockets.pop(sock)
			if sock not in corked:
				poller.unregister(sock)
			else:
				corked.pop(sock)

		if sock in self.errors:
			self.errors.pop(sock)

	def removeClosedReadSocket(self, name, sock):
		pass

	def corkReadSocket(self, name, sock):
		sockets, poller, fdtosock, corked = self.sockets[name]
		if sock in sockets and sock not in corked:
			corked[sock] = True
			poller.unregister(sock)
			res = True
		else:
			res = False

		return res

	def uncorkReadSocket(self, name, sock):
		sockets, poller, fdtosock, corked = self.sockets[name]
		if sock in sockets:
			if corked.pop(sock, None):
				try:
					poller.register(sock, EPOLLIN | EPOLLHUP)
					res = True
				except socket.error, e:
					sockets.pop(sock)
					res = False
					print "ERROR reregistering socket (%s): %s" % (str(sock), str(e))

					if sock not in self.errors:
						self.errors[sock] = name
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
			sockets = {}
			fdtosock = {}
			corked = {}
			self.pollers[poller.fileno()] = name, poller, sockets, fdtosock

			self.sockets[name] = sockets, poller, fdtosock, corked
			self.main.register(poller, EPOLLIN)

	def clearRead(self, name):
		sockets, poller, fdtosock, corked = self.sockets.pop(name, ({}, None, None, None))
		if sockets:
			self.main.unregister(poller)
			self.pollers.pop(poller.fileno(), None)
			poller.close()
			self.setupRead(name)


	def addWriteSocket(self, name, sock):
		sockets, poller, fdtosock, corked = self.sockets[name]
		if sock not in sockets:
			sockets[sock] = True
			try:
				fileno = sock.fileno()
				poller.register(sock, EPOLLOUT | EPOLLHUP)
				res = True
			except socket.error, e:
				sockets.pop(sock)
				res = False
				print "ERROR registering socket (%s): %s" % (str(sock), str(e))

				if sock not in self.errors:
					self.errors[sock] = name
				else:
					print "NOTE: trying to poll closed socket again (addWriteSocket)"
			else:
				fdtosock[fileno] = sock
		else:
			res = False

		return res

	def removeWriteSocket(self, name, sock):
		sockets, poller, fdtosock, corked = self.sockets[name]
		if sock in sockets:
			try:
				fdtosock.pop(sock.fileno(), None)
			except socket.error:
				pass

			sockets.pop(sock)
			if sock not in corked:
				poller.unregister(sock)
			else:
				corked.pop(sock)

		if sock in self.errors:
			self.errors.pop(sock, None)

	def removeClosedWriteSocket(self, name, sock):
		pass

	def corkWriteSocket(self, name, sock):
		sockets, poller, fdtosock, corked = self.sockets[name]
		if sock in sockets and sock not in corked:
			poller.unregister(sock)
			corked[sock] = True
			res = True
		else:
			res = False

		return res

	def uncorkWriteSocket(self, name, sock):
		sockets, poller, fdtosock, corked = self.sockets[name]
		if sock in sockets:
			if corked.pop(sock, None):
				try:
					poller.register(sock, EPOLLOUT | EPOLLHUP)
					res = True
				except socket.error, e:
					sockets.pop(sock)
					res = False
					print "ERROR reregistering socket (%s): %s" % (str(sock), str(e))

					if sock not in self.errors:
						self.errors[sock] = name
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
			sockets = {}
			fdtosock = {}
			corked = {}
			self.pollers[poller.fileno()] = name, poller, sockets, fdtosock

			self.sockets[name] = sockets, poller, fdtosock, corked
			self.main.register(poller, EPOLLIN)

	def clearWrite(self, name):
		sockets, poller, fdtosock, corked = self.sockets.pop(name, ({}, None, None, None))
		if sockets:
			self.main.unregister(poller)
			self.pollers.pop(poller.fileno(), None)
			poller.close()
			self.setupWrite(name)


	def poll(self):
		try:
			res = self.main.poll(self.speed)
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

		for fd, name in self.errors.iteritems():
			response.setdefault(name, []).append(fd)

#			for sock_fd, sock_events in events:
#				if sock_events & select.EPOLLHUP:
#					print "REMOVING SOCKET BECAUSE WE WERE TOLD IT CLOSED", sock_fd
#					sock = fdtosock.pop(sock_fd, None)
#					poller.unregister(sock_fd)
#					sockets.remove(sock)

		return response
