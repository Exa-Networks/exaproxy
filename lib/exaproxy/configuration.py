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

class ConfigurationError (Exception):
	pass

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
		try:
			answer = pwd.getpwnam(_)
			# uid = answer[2]
		except KeyError:
			raise TypeError('user %s is not found on this system' % _)
		return _

	@staticmethod
	def folder(path):
		path = value.unquote(path)
		paths = [
			os.path.normpath(os.path.join(os.path.join(os.sep,*os.path.join(value.location.split(os.sep)[:-3])),path)),
			os.path.normpath(os.path.join('/','etc','exabgp','exabgp.conf',path)),
			os.path.normpath(path)
		]
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
		paths = [
			os.path.normpath(path),
			os.path.normpath(os.path.join(os.path.join(os.sep,*os.path.join(value.location.split(os.sep)[:-3])),path)),
			os.path.normpath(os.path.join(os.path.join(os.sep,*os.path.join(value.location.split(os.sep)[:-3])),'etc','exabgp','resolv.conf')),
			os.path.normpath(os.path.join('/','etc','exabgp','exabgp.conf',path)),
		]
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
		'host'    : (value.unquote,'127.0.0.1'   , 'the host the proxy listen on'),
		'port'    : (value.integer,'31280'       , 'the port the proxy listen on'),
		'timeout' : (value.integer,'5'           , 'time before we ...'),
		'backlog' : (value.integer,'200'         , 'when busy how many connection should the OS keep for us'),
		'speed'   : (value.integer,'2'           , 'when waiting for connection how long are we sleeping for'),
	},
	'redirector' : {
		'program' : (value.exe,'etc/exaproxy/redirector/allow'  , 'the program used to know where to send request'),
		'minimum' : (value.integer,'5'                          , 'minimum number of worker threads (forked program)'),
		'maximum' : (value.integer,'25'                         , 'maximum number of worker threads (forked program)'),
#		'timeout' : (value.integer,'1'                          , 'how long to wait for work before peforming background work'),
	},

	'http' : {
		'x-forwarded-for' : (value.boolean,'true'    , 'insert x-forarded-for headers to webservers'),
		'allow-connect'   : (value.boolean,'true'    , 'allow client to use CONNECT and https connections'),
	},
	'web' : {
		'enabled' : (value.boolean,'true'              , 'enable the built-in webserver'),
		'port'    : (value.integer,'8080'              , 'port on which the web server listen'),
		'html'    : (value.folder,'etc/exaproxy/html'  , 'where are the proxy served pages are taken from'),
	},
	'daemon' : {
		'pidfile'     : (value.unquote,''                    , 'where to save the pid if we manage it'),
		'user'        : (value.user,'nobody'                 , 'user to run as'),
		'daemonise'   : (value.boolean,'false'               , 'should we run in the background'),
		'resolver'    : (value.resolver,'/etc/resolv.conf'   , 'resolver file'),
		'reactor'     : (value.unquote,'select'              , 'what event mechanism to use (select/epoll)'),
	},
	'logger' : {
		'level'         : (value.syslog,'LOG_ERR'  , 'log message with at least the priority SYSLOG.<level>'),
		'destination'   : (value.unquote,'stdout'  , 'where syslog should log'),
		'logger'        : (value.boolean,'true'    , 'log message from the logger subsystem'),
		'signal'        : (value.boolean,'true'    , 'log message from the signal subsystem'),
		'configuration' : (value.boolean,'true'    , 'log message from the configuration subsystem'),
		'supervisor'    : (value.boolean,'true'    , 'log message from the supervisor subsystem'),
		'daemon'        : (value.boolean,'true'    , 'log message from the daemon subsystem'),
		'server'        : (value.boolean,'true'    , 'log message from the server subsystem'),
		'client'        : (value.boolean,'true'    , 'log message from the client subsystem'),
		'manager'       : (value.boolean,'true'    , 'log message from the manager subsystem'),
		'worker'        : (value.boolean,'true'    , 'log message from the worker subsystem'),
		'download'      : (value.boolean,'true'    , 'log message from the download subsystem'),
		'http'          : (value.boolean,'true'    , 'log message from the http subsystem'),
		'client'        : (value.boolean,'true'    , 'log message from the client subsystem'),
	},
	'profile' : {
		'enabled'     : (value.boolean,'false'  , 'enable profiling'),
		'destination' : (value.nop,'stdout'     , 'save profiling to file (instead to the screen on exits)'),
	},
	'proxy' : {
		'name'    : (value.nop,'ExaProxy'   , 'name'),
		'version' : (value.nop,version      , 'version'),
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
				conf = value.unquote(os.environ.get(env_name,'')) \
				    or value.unquote(os.environ.get(env_name.replace('.','_'),'')) \
				    or value.unquote(ini.get(proxy_section,option,nonedict)) \
				    or default[option][1]
			except (ConfigParser.NoSectionError,ConfigParser.NoOptionError),e:
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
	return __configuration

def default ():
	for section,content in defaults.items():
		if section == 'proxy':
			continue
		for option,value in content.items():
			if option == 'proxy':
				continue
			yield 'exaproxy.%s.%s %s: %s. default (%s)' % (section,option,' '*(20-len(section)-len(option)),value[2],value[1])

def ini ():
	for section,values in __configuration.items():
		if section == 'proxy':
			continue
		print '[exaproxy.%s]' % section
		for k,v in values.items():
			print '%s = %s' % (k,v)
		print
		
def env ():
	for section,values in __configuration.items():
		if section == 'proxy':
			continue
		for k,v in values.items():
			print 'exaproxy.%s.%s="%s"' % (section,k,v)
	print