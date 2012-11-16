# encoding: utf-8
"""
daemon.py

Created by Thomas Mangin on 2011-11-29.
Copyright (c) 2011 Exa Networks. All rights reserved.
"""

import os
import sys
import pwd
import errno
import socket
import resource

from .log.logger import Logger

def signed (value):
	if value == sys.maxint:
		return -1
	return value

class Daemon (object):
	def __init__ (self,configuration):
		self.daemonize = configuration.daemon.daemonize
		self.user = configuration.daemon.user
		self.log = Logger('daemon', configuration.log.daemon)
		#mask = os.umask(0137)
		if configuration.daemon.filemax:
			try:
				# default on mac are (256,-1)
				resource.setrlimit(resource.RLIMIT_NOFILE, (configuration.daemon.filemax, -1))
			except (resource.error,ValueError),e:
				soft,hard = resource.getrlimit(resource.RLIMIT_NOFILE)
				self.log.error('could not increase file descriptor limit : %s' % str(e))
				self.log.error('the current limit is %d' % signed(soft))
				self.log.error('the maximum possible limit is %d' % signed(hard))

	def drop_privileges (self):
		"""returns true if we are left with insecure privileges"""
		# os.name can be ['posix', 'nt', 'os2', 'ce', 'java', 'riscos']
		if os.name not in ['posix',]:
			return False

		uid = os.getuid()
		gid = os.getgid()

		if uid and gid:
			return False

		try:
			user = pwd.getpwnam(self.user)
			nuid = int(user.pw_uid)
			ngid = int(user.pw_uid)
		except KeyError:
			return True

		# not sure you can change your gid if you do not have a pid of zero
		try:
			if not uid:
				os.setuid(nuid)
			if not gid:
				os.setgid(ngid)
			return False
		except OSError:
			return True

	def _is_socket (self,fd):
		try:
			s = socket.fromfd(fd, socket.AF_INET, socket.SOCK_RAW)
		except ValueError,e:
			# The file descriptor is closed
			return False
		try:
			s.getsockopt(socket.SOL_SOCKET, socket.SO_TYPE)
		except socket.error, e:
			# It is look like one but it is not a socket ...
			if e.args[0] == errno.ENOTSOCK:
				return False
		return True

	def daemonise (self):
		if not self.daemonize:
			return

		def fork_exit ():
			try:
				pid = os.fork()
				if pid > 0:
					os._exit(0)
			except OSError, e:
				self.log.debug('Can not fork, errno %d : %s' % (e.errno,e.strerror))

		# do not detach if we are already supervised or run by init like process
		if self._is_socket(sys.__stdin__.fileno()) or os.getppid() == 1:
			return

		fork_exit()
		os.setsid()
		fork_exit()
		self.silence()

	def silence (self):
		maxfd = resource.getrlimit(resource.RLIMIT_NOFILE)[1]
		if (maxfd == resource.RLIM_INFINITY):
			maxfd = MAXFD

		for fd in range(0, maxfd):
			try:
				os.close(fd)
			except OSError:
				pass

		os.open("/dev/null", os.O_RDWR)
		os.dup2(0, 1)
		os.dup2(0, 2)

