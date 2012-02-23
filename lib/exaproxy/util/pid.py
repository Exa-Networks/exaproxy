#!/usr/bin/env python
# encoding: utf-8
"""
pid.py

Created by Thomas Mangin on 2011-11-29.
Copyright (c) 2011 Exa Networks. All rights reserved.
"""

#!/usr/bin/env python
# encoding: utf-8
"""
daemon.py

Created by Thomas Mangin on 2011-11-29.
Copyright (c) 2011 Exa Networks. All rights reserved.
"""

import os
import errno

from .logger import logger

class PID (object):
	def __init__ (self,pid_file):
		self.pid_file = pid_file
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
				logger.warning('daemon',"PIDfile already exists, not updated %s" % self.pid_file)
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
				logger.warning('daemon',"PID %s is still running" % self.pid_file)
				return

		ownid = os.getpid()

		flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
		mode = ((os.R_OK | os.W_OK) << 6) | (os.R_OK << 3) | os.R_OK

		try:
			fd = os.open(self.pid_file,flags,mode)
		except OSError, e:
			logger.warning('daemon',"PIDfile already exists, not updated %s" % self.pid_file)
			return

		try:
			f = os.fdopen(fd,'w')
			line = "%d\n" % ownid
			f.write(line)
			f.close()
			self._saved_pid = True
		except IOError, e:
			logger.warning('daemon',"Can not create PIDfile %s" % self.pid_file)
			return
		logger.info('daemon',"Created PIDfile %s with value %d" % (self.pid_file,ownid))

	def remove (self):
		if not self.pid_file or not self._saved_pid:
			return
		try:
			os.remove(self.pid_file)
		except OSError, e:
			if e.errno == errno.ENOENT:
				pass
			else:
				logger.warning('daemon',"Can not remove PIDfile %s" % self.pid_file)
				return
		logger.info('daemon',"Removed PIDfile %s" % self.pid_file)
