#!/usr/bin/env python
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

from .logger import logger

class Daemon (object):
	def __init__ (self,daemonize,user):
		self.daemonize = daemonize
		self.user = user
		#mask = os.umask(0137)
		try:
			# default on mac are (256,-1)
			resource.setrlimit(resource.RLIMIT_NOFILE, (4096, -1))
		except (resource.error,ValueError),e:
			logger.error('daemon','could not increase file descriptor limit : %s' % str(e))
			logger.error('daemon','current limits (soft, hard) are : %s' % str(resource.getrlimit(resource.RLIMIT_NOFILE)))

	def drop_privileges (self):
		"""returns true if we are left with insecure privileges"""
		# os.name can be ['posix', 'nt', 'os2', 'ce', 'java', 'riscos']
		if os.name not in ['posix',]:
			return False

		uid = os.getpid()
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
				logger.debug('daemon','Can not fork, errno %d : %s' % (e.errno,e.strerror))

		# do not detach if we are already supervised or run by init like process
		if not self._is_socket(sys.__stdin__.fileno()) and not os.getppid() == 1:
			fork_exit()
			os.setsid()
			fork_exit()
