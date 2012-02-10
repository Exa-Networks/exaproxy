#!/usr/bin/env python
# encoding: utf-8
"""
configuration.py

Created by Thomas Mangin on 2011-11-29.
Copyright (c) 2011 Exa Networks. All rights reserved.
"""

# XXX: raised exception not caught
# XXX: reloading mid-program not possible
# XXX: validation for path, file, etc not correctly test (ie surely buggy)

import os
import sys
import syslog
import pwd

from .util.logger import logger
from .util.version import version

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

#class log:
#	LOG_DEBUG    = syslog.LOG_DEBUG
#	LOG_INFO     = syslog.LOG_INFO
#	LOG_NOTICE   = syslog.LOG_NOTICE
#	LOG_WARNING  = syslog.LOG_WARNING
#	LOG_ERR      = syslog.LOG_ERR
#	LOG_CRIT     = syslog.LOG_CRIT
#	LOG_ALERT    = syslog.LOG_ALERT
#	LOG_EMERG    = syslog.LOG_EMERG
	

class NoneDict (dict):
	def __getitem__ (self,name):
		return None
nonedict = NoneDict()

class value (object):
	location = os.path.normpath(sys.argv[0]) if sys.argv[0].startswith('/') else os.path.normpath(os.path.join(cwd,sys.argv[0]))
	
	@staticmethod
	def integer (_):
		return int(_)

	@staticmethod
	def unquote (_):
		 return _.strip().strip('\'"')

	@staticmethod
	def nop (_):
		return _

	@staticmethod
	def boolean (_):
		return _.lower() in ('1','yes','on','enable','true')

	@staticmethod
	def user (_):
		# XXX: incomplete
		return pwd.getpwnam(_)[2]

	@staticmethod
	def folder(path):
		path = value.unquote(path)
		paths = {
			os.path.normpath(os.path.join(os.path.join(os.sep,*os.path.join(value.location.split(os.sep)[:-3])),path)),
			os.path.normpath(os.path.join('/','etc','exabgp','exabgp.conf',path)),
			os.path.normpath(path)
		}
		options = [path for path in paths if os.path.exists(path)]
		if not options: raise TypeError('%s does not exists' % path)
		first = options[0]
		if not first: raise TypeError('%s does not exists' % first)
		return first

	@staticmethod
	def conf(path):
		first = value.folder(path)
		if not os.path.isfile(first): raise TypeError('%s is not a file' % path)
		return first

	@staticmethod
	def resolver(path):
		paths = {
			os.path.normpath(path),
			os.path.normpath(os.path.join(os.path.join(os.sep,*os.path.join(value.location.split(os.sep)[:-3])),path)),
			os.path.normpath(os.path.join(os.path.join(os.sep,*os.path.join(value.location.split(os.sep)[:-3])),'etc','exabgp','resolv.conf')),
			os.path.normpath(os.path.join('/','etc','exabgp','exabgp.conf',path)),
		}
		for resolver in paths:
			if os.path.exists(resolver):
				with open(resolver) as r:
					if 'nameserver' in [line.strip().split(None,1)[0].lower() for line in r.readlines()]:
						return resolver
		raise TypeError('resolv.conf can not be found')

	@staticmethod
	def exe (path):
		first = value.conf(path)
		if not os.access(first, os.X_OK): raise TypeError('%s is not an executable' % first)
		return first

	@staticmethod
	def syslog (log):
		if log not in _priorities:
			raise TypeError('invalid log level %s' % log)
		return _priorities[log]

defaults = {
	'tcp' : {
		'host'    : (value.unquote,'127.0.0.1'),
		'port'    : (value.integer,'31280'),
		'timeout' : (value.integer,'5'),
		'backlog' : (value.integer,'200'),
		'speed'   : (value.integer,'2'),
	},
	'redirector' : {
		'program' : (value.exe,'etc/exaproxy/redirector/allow'),
		'minimum' : (value.integer,'5'),
		'maximum' : (value.integer,'25'),
		'timeout' : (value.integer,'1'),
	},

	'http' : {
		'x-forwarded-for' : (value.boolean,'true'),
		'allow-connect'   : (value.boolean,'true'),
	},
	'web' : {
		'enabled' : (value.boolean,'true'),
		'port'    : (value.integer,'8080'),
		'html'    : (value.folder,'etc/exaproxy/html'),
	},
	'daemon' : {
		'pidfile'     : (value.unquote,''),
		'user'        : (value.user,'nobody'),
		'daemonise'   : (value.boolean,'false'),
		'resolver'    : (value.resolver,'/etc/resolv.conf')
	},
	'logger' : {
		'level'         : (value.syslog,'LOG_ERR'),
		'signal'        : (value.boolean,'true'),
		'configuration' : (value.boolean,'true'),
		'main'          : (value.boolean,'true'),
		'supervisor'    : (value.boolean,'true'),
		'daemon'        : (value.boolean,'true'),
		'server'        : (value.boolean,'true'),
		'client'        : (value.boolean,'true'),
		'manager'       : (value.boolean,'true'),
		'worker'        : (value.boolean,'true'),
		'download'      : (value.boolean,'true'),
		'http'          : (value.boolean,'true'),
		'client'        : (value.boolean,'true'),
	},
	'profile' : {
		'enabled'     : (value.boolean,'false'),
		'destination' : (value.nop,'stdout'),
	},
	'proxy' : {
		'name'    : (value.nop,'ExaProxy'),
		'version' : (value.nop,version),
	}
}

import ConfigParser

class Store (dict):
	def __getitem__ (self,key):
		return dict.__getitem__(self,key.replace('_','-'))
	def __setitem__ (self,key,value):
		return dict.__setitem__(self,key.replace('_','-'),value)
	def __getattr__ (self,key):
		return dict.__getitem__(self,key.replace('_','-'))
	def __setattr__ (self,key,value):
		return dict.__setitem__(self,key.replace('_','-'),value)


def _configuration ():
	_conf_paths = (
		os.path.normpath(os.path.join(os.path.join(os.sep,*os.path.join(value.location.split(os.sep)[:-3])),'etc','exaproxy','exaproxy.conf')),
		os.path.normpath(os.path.join('/','etc','exaproxy','exaproxy.conf')),
	)

	ini_file = [path for path in _conf_paths if os.path.exists(path)][0]
	if not ini_file:
		raise ConfigurationError('could not find exabgp.conf file')

	ini = ConfigParser.ConfigParser()
	ini.read(ini_file)

	configuration = Store()

	for section in defaults:
		default = defaults[section]

		for option in default:
			convert = default[option][0]
			try:
				proxy_section = 'exaproxy.%s' % section
				env_name = '%s.%s' % (proxy_section,option)
				conf = value.unquote(os.environ.get(env_name,'')) or value.unquote(ini.get(proxy_section,option,nonedict)) or default[option][1]
			except ConfigParser.NoSectionError:
				conf = default[option][1]
			try:
				configuration.setdefault(section,Store())[option] = convert(conf)
			except TypeError,e:
				raise ConfigurationError('invalid value for %s.%s : %s' % (section,option,conf))

	return configuration

__configuration = None

def load ():
	global __configuration
	if __configuration:
		return __configuration
		
	__configuration = _configuration()

	for section,value in __configuration['logger'].items():
		if section == 'level':
			if _all:
				logger.level = syslog.LOG_DEBUG
			else:
				logger.level = value
		else:
			logger.status[section] = value or _all

	return __configuration
