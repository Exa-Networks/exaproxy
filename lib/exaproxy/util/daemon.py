# encoding: utf-8
"""
daemon.py

Created by Thomas Mangin on 2011-11-29.
Copyright (c) 2011-2013  Exa Networks. All rights reserved.
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
		self.filemax = 0
		self.daemonize = configuration.daemon.daemonize
		self.user = configuration.daemon.user
		self.log = Logger('daemon', configuration.log.daemon)
		#mask = os.umask(0137)

		if configuration.web.debug:
			self.log.critical('WARNING: python remote execution via the web server is enabled')

		if configuration.daemon.reactor == 'epoll' and not sys.platform.startswith('linux'):
			self.log.error('exaproxy.daemon.reactor can only be epoll only on Linux')
			sys.exit(1)

		if configuration.daemon.reactor == 'kqueue' and not sys.platform.startswith('freebsd') and not sys.platform.startswith('darwin'):
			self.log.error('exaproxy.daemon.reactor can only be kqueue only on FreeBSD or OS X')
			sys.exit(1)

		self.nb_descriptors = 40  # some to be safe ...
		self.nb_descriptors += configuration.http.connections*2    # one socket for client and server connection
		self.nb_descriptors += configuration.web.connections       # one socket per web client connection
		self.nb_descriptors += configuration.redirector.maximum*2  # one socket per pipe to the thread and one for the forked process
		self.nb_descriptors += configuration.dns.retries*10        # some sockets for the DNS

		if configuration.daemon.reactor == 'select':
			if self.nb_descriptors > 1024:
				self.log.critical('the select reactor is not very scalable, and can only handle 1024 simultaneous descriptors')
				self.log.critical('your configuration requires %d file descriptors' % self.nb_descriptors)
				self.log.critical('please increase your system maximum limit, alternatively you can reduce')
				self.log.critical('exaproxy.http.connections, exaproxy.web.connections and/or configuration.redirector.maximum')
				return

		soft,hard = resource.getrlimit(resource.RLIMIT_NOFILE)

		if soft < self.nb_descriptors:
			try:
				self.log.warning('not enough file descriptor available, increasing the limit from %d to %d' % (soft,self.nb_descriptors))
				soft_limit,hard_limit = resource.getrlimit(resource.RLIMIT_NOFILE)
				wanted_limit = min(self.nb_descriptors, hard_limit if hard_limit > 0 else self.nb_descriptors)
				# default on mac are (256,-1)
				resource.setrlimit(resource.RLIMIT_NOFILE, (wanted_limit, hard_limit))

			except (resource.error,ValueError),e:
				self.log.warning('problem when trying to increase resource limit : %s' % str(e))

		soft,hard = resource.getrlimit(resource.RLIMIT_NOFILE)
		if soft < self.nb_descriptors:
			self.log.critical('could not increase file descriptor limit to %d, limit is still %d' % (self.nb_descriptors,signed(soft)))
			self.log.critical('please increase your system maximum limit, alternatively you can reduce')
			self.log.critical('exaproxy.http.connections, exaproxy.web.connections and/or configuration.redirector.maximum')
			return

		self.log.info('for information, your configuration requires %d available file descriptors' % self.nb_descriptors)
		self.filemax = self.nb_descriptors

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
			if not gid:
				os.setgid(ngid)
			if not uid:
				os.setuid(nuid)
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
			maxfd = 1024

		for fd in range(0, maxfd):
			try:
				os.close(fd)
			except OSError:
				pass

		os.open("/dev/null", os.O_RDWR)
		os.dup2(0, 1)
		os.dup2(0, 2)
