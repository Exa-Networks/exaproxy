# encoding: utf-8
"""
log.py

Created by Thomas Mangin on 2011-11-29.
Copyright (c) 2011-2013  Exa Networks. All rights reserved.
"""

import os
import sys
import time
import logging
import logging.handlers

from .history import History,Level
from .message import message_store
from .message import usage_store

class RecordedLog (object):
	history = History()


class LogWriter (RecordedLog):
	gidentifier = ['ExaProxy']
	mailbox = None
	debug_level = Level.value.DEBUG

	def writeMessages (self):
		messages = self.mailbox.readMessages() if self.mailbox is not None else []
		messages = ((n,l,t,m) for (n,l,t,m) in messages if l >= self.level) if self.active else []
		for name, level, timestamp, message in messages:
			text = self.formatMessage(name, level, timestamp, message)
			self.writeMessage(level, text)

		self.finishWriting()

	def writeMessage (self, level, message):
		raise NotImplementedError

	def finishWriting (self):
		pass

	def setIdentifier (self, identifier):
		self.gidentifier.append(identifier)
		self.gidentifier.pop(0)

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


class DebugLogWriter(LogWriter):
	mailbox = message_store

	def __init__ (self, active=True, fd=sys.stdout, level=Level.value.WARNING):
		self.pid = os.getpid()
		self.active = active
		self.level = level
		self.fd = fd

	def formatMessage (self, name, level, timestamp, message):
		identifier = self.getIdentifier()
		loglevel = Level.name(level)
		date_string = time.strftime('%a, %d %b %Y %H:%M:%S',timestamp)
		template = '%s %s %-6d %-10s %-13s %%s' % (date_string, identifier, self.pid, loglevel, name)

		return '\n'.join(template % line for line in message.split('\n'))

	def writeMessage (self, level, message):
		self.fd.write('%s\n' % message)

	def finishWriting (self):
		self.fd.flush()


class SysLogWriter(LogWriter):
	mailbox = message_store

	# changing the default level from level=logging.INFO to anything less verbose
	# is likely to break UDP sysloging which sends its message a INFO level
	def __init__ (self, name, destination, active=True, level=Level.value.INFO):
		self.backup = None
		self.pid = os.getpid()
		self.active = active
		self.level = level

		_syslog = logging.getLogger(name)
		for handler in _syslog.handlers:
			_syslog.removeHandler(handler)
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
			if ':' in destination[5:]:
				_host,_port = destination.strip().split(':',1)
				host = _host.rstrip()
				_port = _port.strip()
				if _port.isdigit():
					address = host, int(_port)
			else:
				address = destination[5:].strip(), 514
			handler = logging.handlers.SysLogHandler(address)

		else:
			handler = logging.handlers.RotatingFileHandler(destination, maxBytes=5*1024*1024, backupCount=5)

		return handler


class UsageWriter(SysLogWriter):
	mailbox = usage_store
