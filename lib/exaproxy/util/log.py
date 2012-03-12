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
import socket
import logging
import logging.handlers

class LogManager:
	def __init__(self, poller):
		self.workers = {}
		self.poller = poller

	def addWorker(self, worker):
		self.workers[worker.socket] = worker
		self.poller.addReadSocket('read_log', worker.socket)

	def removeWorker(self, socket):
		worker = self.workers.pop(socket, None)
		if worker:
			self.poller.removeReadSocket('read_log', worker.socket)

	def logItems(self, socket):
		worker = self.workers.get(socket, None)
		if worker is not None:
			worker.writeItems()

class History:
	def __init__ (self):
		self.history = []
		self.length = 100
		self.position = 0

	def record (self, loglevel, message, timestamp):
		self.history.append((loglevel, message, timestamp))

		if self.position >= self.length:
			self.history = self.history[1:]
		else:
			self.position += 1

	def snapshot(self):
		return self.history[:]



class Printer (object):
	def log (self, message):
		#sys.stdout.write('%s %s\n' % (value.upper(),message))
		sys.stdout.write('%s\n' % message)
		sys.stdout.flush()


class Syslog:
	debuglevel = syslog.LOG_DEBUG

	_named_level = {
		syslog.LOG_EMERG   :  'emergency', # 0
		syslog.LOG_ALERT   :  'alert'    , # 1
		syslog.LOG_CRIT    :  'critical' , # 2
		syslog.LOG_ERR     :  'error'    , # 3
		syslog.LOG_WARNING :  'WARNING'  , # 4
		syslog.LOG_NOTICE  :  'NOTICE'   , # 5
		syslog.LOG_INFO    :  'INFO'     , # 6
		syslog.LOG_DEBUG   :  'DEBUG'    , # 7
	}

	def __init__ (self, active, level):
		self.active = active
		self.level = level
		self.oldactive = None
		self.oldlevel = None
	
	def toggleDebug (self):
		if self.oldlevel is not None:
			self.active = self.oldactive
			self.level = self.oldlevel
			self.oldactive = None
			self.oldlevel = None
		else:
			self.oldactive = self.active
			self.oldlevel = self.level
			self.active = True
			self.level = self.debuglevel


class LogWriter(Syslog):
	debug = False
	history = History()
	max_log_items = 20

	def __init__ (self, active, destination, configuration, port=8888, level=syslog.LOG_WARNING):
		if port is not None:
			self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
			self.socket.bind(('127.0.0.1', port))
			self.socket.setblocking(0)
		else:
			self.socket = None
		self.configuration = configuration
		self.active_names = {}
		self.level = level
		self.pid = os.getpid()

		try:
			if destination == 'print':
				issyslog = False
				_syslog = Printer()
			else:
				issyslog, handler = self.getHandler(destination)
				_syslog = logging.getLogger()
				_syslog.addHandler(handler)
				_syslog.setLevel(level)
		except IOError, e:
			print >> sys.stderr, 'Could not use SYSLOG: %s' % str(e)
			sys.exit(1)
		
		self.issyslog = issyslog
		self._syslog = _syslog

		Syslog.__init__(self, active, level)

	def getHandler(self, destination):
		if destination in ('stdout', 'stderr'):
			handler = logging.StreamHandler()
			issyslog = False

		elif destination == '':
			if sys.platform == 'darwin':
				address = '/var/run/syslog'
			else:
				address = '/dev/log'

			if not os.path.exists(address):
				address = 'localhost', 514

			handler = logging.handlers.SysLogHandler(address)
			issyslog = True

		elif destination.lower().startswith('host:'):
			# If the address is invalid, each syslog call will print an error.
			# See how it can be avoided, as the socket error is encapsulated and not returned
			address = (destination[5:].strip(), 514)
			handler = logging.handlers.SysLogHandler(address)
			issyslog = True

		else:
			handler = logging.handlers.RotatingFileHandler(destination, maxBytes=5*1024*1024, backupCount=5)

		return True, handler
		return issyslog, handler

	def getHistory (self):
		def history():
			for text, loglevel, timestamp in self.history.snapshot():
				yield self._format(text, loglevel, timestamp)

		return os.linesep.join(history())

	def _format (self, name, text, timestamp):
		date_string = time.strftime('%a, %d %b %Y %H:%M:%S',timestamp)
		template = '%s %-6d %-13s %%s' % (date_string, self.pid, name)

		return '\n'.join(template % line for line in text.split('\n'))

	def _sys_format (self, name, text):
		for line in text.split('\n'):
			yield 'ExaProxy %-6d %-13s %s' % (self.pid, name, line)

	def logMessage (self, message):
		try:
			name, level, text = message.split('\0', 2)
			# XXX: should be passed in the message to us
			timestamp = time.localtime()
			name = name.split()[0]
		except ValueError:
			name = 'unknown'
			level = 'unknown'
			text = message
			timestamp = time.localtime()

		if self.active is True:
			active = self.active_names.get(name)
		else:
			active = False

		if active is None:
			if hasattr(self.configuration, name):
				active = getattr(self.configuration, name, None)
				if isinstance(active, bool):
					self.active_names[name] = active

		if active is True:
			self.history.record(level, text, timestamp)
			if self.issyslog:
				self.syslog(name, level, text)
			else:
				self.writelog(name, level, text, timestamp)

	def writeItems (self):
		try:
			for _ in xrange(self.max_log_items):
				message, peer = self.socket.recvfrom(65535)
				self.logMessage(message)
		except socket.error, e:
			pass

	def writelog (self, name, loglevel,  message, timestamp):
		text = self._format(name, message, timestamp)
		self._syslog.log(text)

	def syslog (self, name, loglevel, message):
		if loglevel <= self.level:
			logger = getattr(self, 'log_' + loglevel, None)
			if logger is not None:
				for line in self._sys_format(name, message):
					logger(line)

	# wrappers to avoid exposing methods of self._syslog we don't want
	# to be visible when supplying loglevel to getattr()

	def log_debug (self, message):
		self._syslog.debug(message)

	def log_info (self, message):
		self._syslog.info(message)

	def log_notice (self, message):
		self._syslog.notice(message)

	def log_warning (self, message):
		self._syslog.warning(message)

	def log_error (self, message):
		self._syslog.error(message)

	def log_critical (self, message):
		self._syslog.critical(message)

	def log_alert (self, message):
		self._syslog.alert(message)

	def log_emergency (self, message):
		self._syslog.emergency(message)



class Logger(Syslog):
	facility = syslog.LOG_DAEMON

	def __init__(self, name, active, port=8888, level=syslog.LOG_DEBUG):
		self.name = str(name)
		self.destination = ('127.0.0.1', port)
		Syslog.__init__(self, active, level)


	def log (self, text, loglevel):
		if self.active is True and loglevel <= self.level:
			levelname = self._named_level.get(loglevel, 'unknown')
			message = '\0'.join((self.name, levelname, text))
			s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
			return s.sendto(message, self.destination)

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


class UsageLogger(Logger):
	def logRequest (self, client_id, client_ip, command, url, status, destination):
		if self.active:
			now = time.time()
			line = '%s %.02f %s %s %s %s %s/%s' % (
				time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(now)),
				now, client_id, client_ip, command, url, status, destination
			)

			self.log(line, syslog.LOG_NOTICE)



#
#if __name__ == '__main__':
#	class config:
#		log = {'test':'active'}
#
#	logger = Logger('test', config)
#	logger.notice('This is a test message')
