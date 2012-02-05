#!/usr/bin/env python
# encoding: utf-8
"""
configuration.py

Created by Thomas Mangin on 2011-11-29.
Copyright (c) 2011 Exa Networks. All rights reserved.
"""

from .util.version import version

import os
import sys
import syslog

from .util.logger import logger
from .util.version import version

_enabled = ('1','yes','on','enable')
_all = os.environ.get('DEBUG_ALL','0') != '0'

_priorities = {
	'LOG_EMERG'    : syslog.LOG_EMERG,
	'LOG_ALERT'    : syslog.LOG_ALERT,
	'LOG_CRIT'     : syslog.LOG_CRIT,
	'LOG_ERR'      : syslog.LOG_ERR,
	'LOG_WARNING'  : syslog.LOG_WARNING,
	'LOG_NOTICE'   : syslog.LOG_NOTICE,
	'LOG_INFO'     : syslog.LOG_INFO,
	'LOG_DEBUG'    : syslog.LOG_DEBUG,
}

class log:
	LOG_DEBUG    = syslog.LOG_DEBUG
	LOG_INFO     = syslog.LOG_INFO
	LOG_NOTICE   = syslog.LOG_NOTICE
	LOG_WARNING  = syslog.LOG_WARNING
	LOG_ERR      = syslog.LOG_ERR
	LOG_CRIT     = syslog.LOG_CRIT
	LOG_ALERT    = syslog.LOG_ALERT
	LOG_EMERG    = syslog.LOG_EMERG
	

class _Configuration (object):
	_instance = None

	HOST      = os.environ.get('HOST','127.0.0.1') # tcp host for proxy
	PORT      = int(os.environ.get('PORT')) if os.environ.get('PORT','').isdigit() else 31280 # tcp port for proxy
	TIMEOUT   = int(os.environ.get('TIMEOUT')) if os.environ.get('TIMEOUT','').isdigit() else 5 # tcp connection timeout
	BACKLOG   = int(os.environ.get('BACKLOG')) if os.environ.get('BACKLOG','').isdigit() else 200 # tcp connection backlog
	SPEED     = 2 # select waiting timeout

	PID       = os.environ.get('PID','') # where to save the PID if we do
	USER      = os.environ.get('USER','nobody') # whatuser right to use if we are root
	DAEMONIZE = os.environ.get('DAEMONIZE','0').lower() in _enabled # should the program become a daemon

	VERSION   = version # version of the program
	PROGRAM   = (sys.argv + ['', ''])[1] # program name used

	CONNECT   = os.environ.get('CONNECT','1').lower() in _enabled # do we allow the CONNECT method
	PROFILE   = os.environ.get('PROFILE','0') # Turn on profiling and if a file (ie not 0/1) save the result there
	RESOLV    = os.environ.get('RESOLV', '/etc/resolv.conf') # The resolver file to use
	MIN_WORK  = int(os.environ.get('MIN_WORKERS')) if os.environ.get('MIN_WORKERS','').isdigit() else 5 # how many worker thread will we always have
	MAX_WORK  = int(os.environ.get('MAX_WORKERS')) if os.environ.get('MAX_WORKERS','').isdigit() else 25 # how many worker thread is our maximum

	_location = os.path.normpath(sys.argv[0]) if sys.argv[0].startswith('/') else os.path.normpath(os.path.join(cwd,sys.argv[0]))
	_paths = (
		os.path.join(os.path.join(os.sep,*os.path.join(_location.split(os.sep)[:-3])),'etc','exaproxy','html'),
		os.path.normpath('/etc/exaproxy/html'),
	)

	HTML      = [path for path in _paths if os.path.exists(path)][0] # XXX: This will fail if we can not find a configuration location

	def __init__ (self):
		if os.environ.get('SYSLOG',None):
			logger.syslog()
		logger.level = _priorities.get(os.environ.get('LOG',None),syslog.LOG_DEBUG if _all else syslog.LOG_ERR)
		
		for section in ('main','supervisor','daemon','server','client','manager','worker','download','http','client'):
			enabled = os.environ.get('DEBUG_%s' % section.upper(),'0').lower() in _enabled or _all
			logger.status[section] = enabled

def Configuration ():
	if _Configuration._instance:
		return _Configuration._instance
	instance = _Configuration()
	_Configuration._instance = instance
	return instance

configuration = Configuration()
