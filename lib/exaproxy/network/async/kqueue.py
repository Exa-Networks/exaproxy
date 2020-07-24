# encoding: utf-8
"""
kqueue.py

Created by Marek Obuchowicz, KoreKontrol.eu, 2014-05-20
"""

import select
import errno
import socket
import datetime

from interface import IPoller

from select import KQ_FILTER_READ, KQ_FILTER_WRITE, KQ_EV_ADD, KQ_EV_DELETE, kevent
# KQ_EV_ENABLE, KQ_EV_DISABLE,
# KQ_EV_CLEAR, KQ_EV_ONESHOT,
# KQ_EV_ERROR,
# KQ_EV_EOF,


from exaproxy.util.log.logger import Logger
from exaproxy.configuration import load

configuration = load()
log = Logger('select', configuration.log.server)

class KQueuePoller (IPoller):
	kqueue = staticmethod(select.kqueue)

	def __init__(self, speed):
		self.speed = speed

		self.sockets = {}
		self.pollers = {}
		self.main = self.kqueue()
		self.errors = {}
		self.max_events = 10000

	def addReadSocket(self, name, sock):
		sockets, poller, fdtosock, corked = self.sockets[name]
		if sock not in sockets:
			sockets[sock] = True
			try:
				fileno = sock.fileno()
				assert fdtosock.get(fileno, None) is None
				fdtosock[fileno] = sock

				poller.control([kevent(sock, KQ_FILTER_READ, KQ_EV_ADD)], 0)
				res = True
			except socket.error, e:
				if fdtosock.get(fileno, None):
					del fdtosock[fileno]

				sockets.pop(sock)
				res = False
				print "ERROR registering kqueue socket (%s): %s" % (str(sock), str(e))

				if sock not in self.errors:
					self.errors[sock] = name
				else:
					print "NOTE: trying to poll closed socket again (addReadSocket)"
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
				poller.control([kevent(sock, KQ_FILTER_READ, KQ_EV_DELETE)], 0)
			else:
				corked.pop(sock)

		if sock in self.errors:
			self.errors.pop(sock)

	def removeClosedReadSocket (self, name, sock):
		print "%s - KQ: ignore remove closed read socket %d" % (str(datetime.datetime.now()), sock.fileno())

	def corkReadSocket(self, name, sock):
		sockets, poller, fdtosock, corked = self.sockets[name]
		if sock in sockets and sock not in corked:
			corked[sock] = True
			poller.control([kevent(sock, KQ_FILTER_READ, KQ_EV_DELETE)], 0)
			res = True
		else:
			res = False

		return res

	def uncorkReadSocket(self, name, sock):
		sockets, poller, fdtosock, corked = self.sockets[name]
		if sock in sockets:
			if corked.pop(sock, None):
				try:
					poller.control([kevent(sock, KQ_FILTER_READ, KQ_EV_ADD)], 0)
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
			poller = self.kqueue()
			sockets = {}
			fdtosock = {}
			corked = {}

			self.pollers[poller.fileno()] = name, poller, sockets, fdtosock
			self.sockets[name] = sockets, poller, fdtosock, corked

			self.main.control([kevent(poller, KQ_FILTER_READ, KQ_EV_ADD)], 0)

	def clearRead(self, name):
		sockets, poller, fdtosock, corked = self.sockets.pop(name, ({}, None, None, None))
		if sockets:
			self.main.control([kevent(poller, KQ_FILTER_READ, KQ_EV_DELETE)], 0)
			self.pollers.pop(poller.fileno(), None)
			poller.close()
			self.setupRead(name)


	def addWriteSocket(self, name, sock):
		sockets, poller, fdtosock, corked = self.sockets[name]
		if sock not in sockets:
			sockets[sock] = True
			try:
				fileno = sock.fileno()
				assert fdtosock.get(fileno, None) is None
				fdtosock[fileno] = sock

				poller.control([kevent(sock, KQ_FILTER_WRITE, KQ_EV_ADD)], 0)
				res = True
			except socket.error, e:
				if fdtosock.get(fileno, None):
					del fdtosock[fileno]

				sockets.pop(sock)
				res = False
				print "ERROR registering kqueue socket (%s): %s" % (str(sock), str(e))

				if sock not in self.errors:
					self.errors[sock] = name
				else:
					print "NOTE: trying to poll closed socket again (addReadSocket)"
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
				poller.control([kevent(sock, KQ_FILTER_WRITE, KQ_EV_DELETE)], 0)
			else:
				corked.pop(sock)

		if sock in self.errors:
			self.errors.pop(sock)

	def removeClosedWriteSocket(self, name, sock):
		print "%s - KQ: ignore remove closed write socket %d" % (str(datetime.datetime.now()), sock.fileno())

	def corkWriteSocket(self, name, sock):
		sockets, poller, fdtosock, corked = self.sockets[name]
		if sock in sockets and sock not in corked:
			corked[sock] = True
			poller.control([kevent(sock, KQ_FILTER_WRITE, KQ_EV_DELETE)], 0)
			res = True
		else:
			res = False

		return res

	def uncorkWriteSocket(self, name, sock):
		sockets, poller, fdtosock, corked = self.sockets[name]
		if sock in sockets:
			if corked.pop(sock, None):
				try:
					poller.control([kevent(sock, KQ_FILTER_WRITE, KQ_EV_ADD)], 0)
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

	def setupWrite(self, name):
		if name not in self.sockets:
			poller = self.kqueue()
			sockets = {}
			fdtosock = {}
			corked = {}

			self.pollers[poller.fileno()] = name, poller, sockets, fdtosock
			self.sockets[name] = sockets, poller, fdtosock, corked

			self.main.control([kevent(poller, KQ_FILTER_READ, KQ_EV_ADD)], 0)


	def clearWrite(self, name):
		sockets, poller, fdtosock, corked = self.sockets.pop(name, ({}, None, None, None))
		if sockets:
			self.main.control([kevent(poller, KQ_FILTER_READ, KQ_EV_DELETE)], 0)
			self.pollers.pop(poller.fileno(), None)
			poller.close()
			self.setupRead(name)

	def poll(self):
		try:
			res = self.main.control(None, self.max_events, self.speed)
		except EnvironmentError, e:
			if e.errno != errno.EINTR:
				log.critical('KQueue main poller - unexpected error')
				raise

			res = []
			response = {}
		else:
			# response['poller1']=[] ; response['poller2']=[] etc.
			response = dict((name, []) for (name, _, _, _) in self.pollers.values())
			if len(res) == self.max_events:
				log.warning("polled max_events from main kqueue")

		for events in res:
			fd = events.ident

			name, poller, sockets, fdtosock = self.pollers[fd]
			events = poller.control(None, self.max_events, 0)

			if len(events) == self.max_events:
				log.warning("polled max_events from queue %s" % name)

			for sock_events in events:
				sock_fd = sock_events.ident
				try:
					response[name].append(fdtosock[sock_fd])
				except KeyError:
					log.error("KQueue register called before fdtosock registered! Skipping event")
					continue

				if sock_events.flags & select.KQ_EV_ERROR:
					log.warning("%s KQ_EV_ERROR: fd=%d filter=%d fflags=%d flags=%d data=%d udata=%d" % (
						str(datetime.datetime.now()),
						sock_events.ident, sock_events.filter, sock_events.flags, sock_events.fflags,
						sock_events.data, sock_events.udata))

					sock = fdtosock.pop(sock_fd, None)
					poller.control([kevent(sock, sock_events.filter, KQ_EV_DELETE)], 0)
					sockets.pop(sock)

					if sock not in self.errors:
						self.errors[sock] = name

		for fd, name in self.errors.iteritems():
			response.setdefault(name, []).append(fd)

		return response
