
import time
import logging
from collections import deque

class Level:
	class value:
		DEBUG = logging.DEBUG
		INFO = logging.INFO
		WARNING = logging.WARNING
		ERROR = logging.ERROR
		CRITICAL = logging.CRITICAL

	string = {
		value.DEBUG : 'debug',
		value.INFO : 'info',
		value.WARNING : 'warning',
		value.ERROR : 'error',
		value.CRITICAL : 'critical',
	}

	@staticmethod
	def name (level):
		return Level.string.get(level, 'UNKNOWN')


class _History:
	_log = None
	_err = None

	def __init__ (self, size):
		self.size = size
		self.messages = deque()

	def record (self, timestamp, name, level, text):
		message = timestamp, name, level, text
		self.messages.append(message)
		if len(self.messages) > self.size:
			self.messages.popleft()

	def snapshot (self):
		return list(self.messages)

	def formated (self):
		for timestamp, name, level, text in self.snapshot():
			date = time.strftime('%a, %d %b %Y %H:%M:%S',timestamp)
			yield '%s %s %-13s %s' % (date, name, Level.name(level), text)

def History (size=1000):
	if not _History._log:
		_History._log = _History(size)
	return _History._log

def Errors (size=1000):
	if not _History._err:
		_History._err = _History(size)
	return _History._err
