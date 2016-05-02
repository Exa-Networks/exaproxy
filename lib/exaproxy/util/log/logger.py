# encoding: utf-8
"""
log.py

Created by Thomas Mangin on 2011-11-29.
Copyright (c) 2011-2013  Exa Networks. All rights reserved.
"""

import time
import logging

from .message import message_store
from .message import usage_store
from .history import History


class Logger:
	mailbox = message_store
	history = History()

	def __init__ (self, name, active=True, loglevel=logging.DEBUG):
		self.name = str(name)
		self.active = active
		self.loglevel = loglevel

	def log (self, text, loglevel):
		now = time.localtime()
		self.history.record(now, self.name, loglevel, text)

		if self.active is True and loglevel >= self.loglevel:
			self.mailbox.addMessage((self.name, loglevel, now, text))
			res = True
		else:
			res = None

		return res

	def stdout (self, message):
		print message

	def debug (self, message):
		self.log(message, logging.DEBUG)

	def info (self, message):
		self.log(message, logging.INFO)

	def notice (self, message):
		self.log(message, logging.INFO)

	def warning (self, message):
		self.log(message, logging.WARNING)

	def error (self, message):
		self.log(message, logging.ERROR)

	def critical (self, message):
		self.log(message, logging.CRITICAL)

	def alert (self, message):
		self.log(message, logging.WARNING)

	def emergency (self, message):
		self.log(message, logging.CRITICAL)


class UsageLogger (Logger):
	mailbox = usage_store

	def logRequest (self, client_id, accept_ip, client_ip, command, url, status, destination):
		if self.active:
			now = time.time()
			line = '%s %.02f %s %s %s %s %s/%s' % (
				time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(now)),
				now, client_id, accept_ip, client_ip, command, url, status, destination
			)

			res = self.log(line, logging.INFO)
		else:
			res = None

		return res
