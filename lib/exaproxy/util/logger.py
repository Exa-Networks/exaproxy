#!/usr/bin/env python
# encoding: utf-8
"""
log.py

Created by Thomas Mangin on 2011-11-29.
Copyright (c) 2011 Exa Networks. All rights reserved.
"""

#!/usr/bin/env python
# encoding: utf-8
"""
utils.py

Created by Thomas Mangin on 2009-09-06.
Copyright (c) 2009-2011 Exa Networks. All rights reserved.
"""

import os
import sys
import time
import syslog
import logging
import logging.handlers

from threading import Lock

_named_level = {
	syslog.LOG_EMERG   :  'EMERGENCY', # 0
	syslog.LOG_ALERT   :  'ALERT'    , # 1
	syslog.LOG_CRIT    :  'CRITICAL' , # 2
	syslog.LOG_ERR     :  'ERROR'    , # 3
	syslog.LOG_WARNING :  'WARNING'  , # 4
	syslog.LOG_NOTICE  :  'NOTICE'   , # 5
	syslog.LOG_INFO    :  'INFO'     , # 6
	syslog.LOG_DEBUG   :  'DEBUG'    , # 7
}

def hex_string (value):
	return '%s' % [(hex(ord(_))) for _ in value]

def single_line (value):
	return '[%s]' % value.replace('\r\n','\\r\\n')


class Printer (object):
	def __getattr__ (self,value):
		def _print (message):
			#sys.stdout.write('%s %s\n' % (value.upper(),message))
			sys.stdout.write('%s\n' % message)
			sys.stdout.flush()
		return _print

class LazyFormat (object):
	def __init__ (self,prefix,format,message):
		self.prefix = prefix
		self.format = format
		self.message = message
	
	def __str__ (self):
		if self.format:
			return self.prefix + self.format(self.message)
		return self.prefix + self.message
	
	def split (self,c):
		return str(self).split(c)

class _Logger (object):
	_instance = None
	_syslog = None

	_inserted = 0
	_max_history = 20
	_history = []
	_lock = Lock()
	
	_config = ''
	_pid = os.getpid()
	
	_toggle_level = None
	_toggle_status = {}
	
	pdb = False

	# we use os.pid everytime as we may fork and the class is instance before it

	def toggle (self):
		if self._toggle_level:
			self.level = self._toggle_level
			self.status = {}
			for k,v in self._toggle_status.items():
				self.status[k] = v
			self._toggle_level = None
			self._toggle_status = {}
		else:
			self._toggle_level = self.level
			self.level = syslog.LOG_DEBUG
			for k,v in self.status.items():
				self._toggle_status[k] = v
				self.status[k] = True

	def history (self):
		with self._lock:
			return '\n'.join(self._format(*_) for _ in self._history)

	def _record (self,timestamp,level,source,message):
		with self._lock:
			self._history.append((timestamp,level,source,message))
			if len(self._history) > self._max_history:
				self._history.pop(0)

	def _format (self,timestamp,level,source,message):
		now = time.strftime('%a, %d %b %Y %H:%M:%S',timestamp)
		return '%s %-9s %-6d %-13s %s' % (now,_named_level[level],self._pid,source,message)

	def _prefixed (self,level,source,message):
		ts = time.localtime()
		self._record(ts,level,source,message)
		return self._format(ts,level,source,message)

	def __init__ (self):
		self.level = syslog.LOG_WARNING
		self.status = {}
		self._syslog = None

	def syslog (self,destination):
		try:
			if destination == 'print':
				self._syslog = Printer()
				return
			if destination in ('stdout','stderr'):
				handler = logging.StreamHandler()
			elif destination == '':
				if sys.platform == 'darwin':
					address = '/var/run/syslog'
				else:
					address = '/dev/log'
				if not os.path.exists(address):
					address = ('localhost', 514)
				handler = logging.handlers.SysLogHandler(address)
			elif destination.lower().startswith('host:'):
				# If the address is invalid, each syslog call will print an error.
				# See how it can be avoided, as the socket error is encapsulated and not returned
				address = (destination[5:].strip(), 514)
				handler = logging.handlers.SysLogHandler(address)
			else:
				handler = logging.handlers.RotatingFileHandler(destination, maxBytes=5*1024*1024, backupCount=5)
			self._syslog = logging.getLogger()
			self._syslog.setLevel(logging.DEBUG)
			self._syslog.addHandler(handler)
		except IOError,e :
			self.error('logger','could not use SYSLOG %s' % str(e))

	def log (self,source,message,level):
		if level <= syslog.LOG_ERR and self.pdb:
			logger.level = syslog.LOG_EMERG # silence the logger as we debug
			import pdb
			pdb.set_trace()

		if not self.status.get(source.split(' ',1)[0],False):
			#print "--recording", level, source, message
			self._record(time.localtime(),level,source,message)

		for line in message.split('\n'):
			if level <= self.level:
					yield self._prefixed(level,source,line)

	def debug (self,source,message):
		for log in self.log(source,message,syslog.LOG_DEBUG):
			self._syslog.debug(log)

	def info (self,source,message):
		for log in self.log(source,message,syslog.LOG_INFO):
			self._syslog.info(log)

	def notice (self,source,message):
		for log in self.log(source,message,syslog.LOG_NOTICE):
			self._syslog.notice(log)

	def warning (self,source,message):
		for log in self.log(source,message,syslog.LOG_WARNING):
			self._syslog.warning(log)

	def error (self,source,message):
		for log in self.log(source,message,syslog.LOG_ERR):
			self._syslog.error(log)

	def critical (self,source,message):
		for log in self.log(source,message,syslog.LOG_CRIT):
			self._syslog.critical(log)

	def alert (self,source,message):
		for log in self.log(source,message,syslog.LOG_ALERT):
			self._syslog.alert(log)

	def emmergency (self,source,message):
		for log in self.log(source,message,syslog.LOG_EMERG):
			self._syslog.emmergency(log)

def Logger ():
	if _Logger._instance:
		return _Logger._instance
	instance = _Logger()
	_Logger._instance = instance
	return instance

logger = Logger()

if __name__ == '__main__':
	logger = Logger()
	logger.debug('source','debug test')
	
