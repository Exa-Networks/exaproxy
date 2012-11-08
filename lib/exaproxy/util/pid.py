# encoding: utf-8
"""
pid.py

Created by Thomas Mangin on 2011-11-29.
Copyright (c) 2011 Exa Networks. All rights reserved.
"""

# encoding: utf-8
"""
daemon.py

Created by Thomas Mangin on 2011-11-29.
Copyright (c) 2011 Exa Networks. All rights reserved.
"""

import os
import errno

from .log.logger import Logger

class PID (object):
	def __init__ (self, configuration):
		self.log = Logger('daemon', configuration.log.daemon)
		self.pid_file = configuration.daemon.pidfile
		self._saved_pid = False
		#mask = os.umask(0137)

	def save (self):
		self._saved_pid = False

		if not self.pid_file:
			return

		try:
			with open(self.pid_file,"r") as f:
				running_pid = int(f.read() or 0)
				if running_pid <= 0:
					return
		except IOError, e:
			# No such file or directory
			if e[0] == errno.ENOENT:
				pass
			if e[0] in (errno.EPERM,errno.EACCES):
				self.log.warning("PIDfile already exists, not updated %s" % self.pid_file)
				return
			raise
		except ValueError, e:
			# Non numeric data in PID file
			pass

		try:
			os.kill(running_pid, 0)
		except OSError, e:
			# No such processs
			if e[0] != errno.ESRCH:
				self.log.warning("PID %s is still running" % self.pid_file)
				return

		ownid = os.getpid()

		flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
		mode = ((os.R_OK | os.W_OK) << 6) | (os.R_OK << 3) | os.R_OK

		try:
			fd = os.open(self.pid_file,flags,mode)
		except OSError, e:
			self.log.warning("PIDfile already exists, not updated %s" % self.pid_file)
			return

		try:
			f = os.fdopen(fd,'w')
			line = "%d\n" % ownid
			f.write(line)
			f.close()
			self._saved_pid = True
		except IOError, e:
			self.log.warning("Can not create PIDfile %s" % self.pid_file)
			return
		self.log.info("Created PIDfile %s with value %d" % (self.pid_file,ownid))

	def remove (self):
		if not self.pid_file or not self._saved_pid:
			return
		try:
			os.remove(self.pid_file)
		except OSError, e:
			if e.errno == errno.ENOENT:
				pass
			else:
				self.log.warning("Can not remove PIDfile %s" % self.pid_file)
				return
		self.log.info("Removed PIDfile %s" % self.pid_file)
