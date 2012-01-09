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
	
	PID       = os.environ.get('PID','')
	USER      = os.environ.get('USER','nobody')
	DAEMONIZE = os.environ.get('DAEMONIZE','0') not in ['','1','yes','Yes','YES']
	VERSION   = version
	PROGRAM   = dict(zip(range(len(sys.argv)),sys.argv)).get(1,'') # I must like perl :)
	SPEED     = 2 # 0.01
	CONNECT   = os.environ.get('CONNECT','1').lower() in _enabled
	PROFILE   = os.environ.get('PROFILE','0')
	CONTENT   = os.environ.get('CONTENT', '/etc/content')

	def __init__ (self):
		if os.environ.get('SYSLOG',None):
			logger.syslog()
		logger.level = _priorities.get(os.environ.get('LOG',None),syslog.LOG_DEBUG if _all else syslog.LOG_ERR)
		
		for section in ('main','supervisor','daemon','server','client','manager','worker','download','http','browser'):
			enabled = os.environ.get('DEBUG_%s' % section.upper(),'0').lower() in _enabled or _all
			logger.status[section] = enabled

def Configuration ():
	if _Configuration._instance:
		return _Configuration._instance
	instance = _Configuration()
	_Configuration._instance = instance
	return instance

configuration = Configuration()
