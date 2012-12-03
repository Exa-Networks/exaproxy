# encoding: utf-8
"""
log.py

Created by Thomas Mangin on 2011-11-29.
Copyright (c) 2011 Exa Networks. All rights reserved.
"""

import os
import sys
import time
import syslog
import logging
import logging.handlers

from .history import History
from .message import message_store


class LogWriter:
	gidentifier = ['ExaProxy']
	history = History()
	mailbox = message_store
	debug_level = syslog.LOG_DEBUG

	levels = {
		syslog.LOG_DEBUG : 'debug', syslog.LOG_INFO : 'info',
		syslog.LOG_NOTICE : 'notice', syslog.LOG_WARNING : 'warning',
		syslog.LOG_ERR : 'error', syslog.LOG_CRIT : 'critical',
		syslog.LOG_ALERT : 'alert', syslog.LOG_EMERG : 'emergency',
	}

	def writeMessages (self):
		messages = self.mailbox.readMessages()
		messages = self.active and ((n,l,t,m) for (n,l,t,m) in messages if l <= self.level) or []

		for name, level, timestamp, message in messages:
			text = self.formatMessage(name, level, timestamp, message)
			self.history.record(level, text, timestamp)
			self.writeMessage(level, text)

		self.finishWriting()

	def writeMessage (self, message):
		raise NotImplementedError

	def finishWriting (self):
		pass

	def setIdentifier (self, identifier):
		self.gidentifier = [identifier]

	def getIdentifier (self):
		return self.gidentifier[0]

	def toggleDebug (self):
		if self.backup is not None:
			(active, level) = self.backup
			self.backup = None
			self.active = active
			self.level = level
		else:
			self.backup = (self.active, self.level)
			self.active = True
			self.level = self.debug_level

	def getHistory (self):
		return self.history.snapshot()


class DebugLogWriter(LogWriter):
	def __init__ (self, active=True, fd=sys.stdout, level=syslog.LOG_WARNING):
		self.pid = os.getpid()
		self.active = active
		self.level = level
		self.fd = fd

	def formatMessage (self, name, level, timestamp, message):
		identifier = self.getIdentifier()
		loglevel = self.levels.get(level, 'UNKNOWN')
		date_string = time.strftime('%a, %d %b %Y %H:%M:%S',timestamp)
		template = '%s %s %-6d %-10s %-13s %%s' % (date_string, identifier, self.pid, loglevel, name)

		return '\n'.join(template % line for line in message.split('\n'))

	def writeMessage (self, level, message):
		self.fd.write('%s\n' % message)

	def finishWriting (self):
		self.fd.flush()


class SysLogWriter(LogWriter):
	def __init__ (self, destination, active=True, level=syslog.LOG_WARNING):
		self.backup = None
		self.pid = os.getpid()
		self.active = active
		self.level = level

		_syslog = logging.getLogger()
		_handler = self.getHandler(destination)
		_syslog.addHandler(_handler)
		_syslog.setLevel(level)

		self._syslog = _syslog

	def formatMessage (self, name, level, timestamp, message):
		identifier = self.getIdentifier()
		return '%s %-6d %-13s %s' % (identifier, self.pid, name, message)

	def writeMessage (self, level, message):
		self._syslog.log(level, message)

	def getHandler (self, destination):
		if destination in ('stdout', 'stderr'):
			handler = logging.StreamHandler()

		elif destination == '':
			if sys.platform == 'darwin':
				address = '/var/run/syslog'
			else:
				address = '/dev/log'

			if not os.path.exists(address):
				address = 'localhost', 514

			handler = logging.handlers.SysLogHandler(address)

		elif destination.lower().startswith('host:'):
			address = destination[5:].strip(), 514
			handler = logging.handlers.SysLogHandler(address)

		else:
			handler = logging.handlers.RotatingFileHandler(destination, maxBytes=5*1024*1024, backupCount=5)

		return handler
