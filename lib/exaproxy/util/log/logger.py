# encoding: utf-8
"""
log.py

Created by Thomas Mangin on 2011-11-29.
Copyright (c) 2011 Exa Networks. All rights reserved.
"""

import time
import syslog

from .message import message_store

class Logger:
	mailbox = message_store

	def __init__ (self, name, active=True, loglevel=syslog.LOG_DEBUG):
		self.name = str(name)
		self.active = active
		self.loglevel = loglevel

	def log (self, text, loglevel):
		if self.active is True and loglevel <= self.loglevel:
			timestamp = time.localtime()
			message = self.name, loglevel, timestamp, text
			self.mailbox.addMessage(message)

			res = True
		else:
			res = None

		return res

	def stdout (self, message):
		print message

	def debug (self, message):
		self.log(message, syslog.LOG_DEBUG)

	def info (self, message):
		self.log(message, syslog.LOG_INFO)

	def notice (self, message):
		self.log(message, syslog.LOG_NOTICE)

	def warning (self, message):
		self.log(message, syslog.LOG_WARNING)

	def error (self, message):
		self.log(message, syslog.LOG_ERR)

	def critical (self, message):
		self.log(message, syslog.LOG_CRIT)

	def alert (self, message):
		self.log(message, syslog.LOG_ALERT)

	def emergency (self, message):
		self.log(message, syslog.LOG_EMERG)


class UsageLogger (Logger):
	def logRequest (self, client_id, client_ip, command, url, status, destination):
		if self.active:
			now = time.time()
			line = '%s %.02f %s %s %s %s %s/%s' % (
				time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(now)),
				now, client_id, client_ip, command, url, status, destination
			)

			res = self.log(line, syslog.LOG_NOTICE)
		else:
			res = None

		return res
