# encoding: utf-8
"""
child.py

Created by David Farrar on 2014-04-21.
Copyright (c) 2011-2013  Exa Networks. All rights reserved.
"""

import subprocess
import fcntl
import os
import errno

from exaproxy.util.log.logger import Logger

class ChildFactory:
	def preExec (self):
		os.setpgrp()

	def __init__ (self, configuration, name):
		self.log = Logger('worker ' + str(name), configuration.log.worker)

	def createProcess (self, program, universal=False):
		try:
			process = subprocess.Popen([program],
				stdin=subprocess.PIPE,
				stdout=subprocess.PIPE,
				stderr=subprocess.PIPE,
				universal_newlines=universal,
				preexec_fn=self.preExec,
			)

			self.log.debug('spawn process %s' % program)

		except KeyboardInterrupt:
			process = None

		except (subprocess.CalledProcessError,OSError,ValueError):
			self.log.error('could not spawn process %s' % program)
			process = None

		if process:
			try:
				fcntl.fcntl(process.stderr, fcntl.F_SETFL, os.O_NONBLOCK)
			except IOError:
				self.destroyProcess(process)
				process = None

		return process

	def destroyProcess (self, process):
		try:
			process.terminate()
			process.wait()
			self.log.info('terminated process PID %s' % process.pid)

		except OSError, e:
			# No such processs
			if e[0] != errno.ESRCH:
				self.log.error('PID %s died' % process.pid)
