# encoding: utf-8
"""
configuration.py

Created by Thomas Mangin on 2011-11-29.
Copyright (c) 2011-2013  Exa Networks. All rights reserved.
"""

# XXX: raised exception not caught
# XXX: reloading mid-program not possible
# XXX: validation for path, file, etc not correctly test (ie surely buggy)

import os
import sys
import logging
import pwd

class ConfigurationError (Exception):
	pass

_syslog_name_value = {
	'CRITICAL'     : logging.CRITICAL,
	'ERROR'        : logging.ERROR,
	'WARNING'      : logging.WARNING,
	'INFO'         : logging.INFO,
	'DEBUG'        : logging.DEBUG,
}

_syslog_value_name = {
	logging.CRITICAL   : 'CRITICAL',
	logging.ERROR      : 'ERROR',
	logging.WARNING    : 'WARNING',
	logging.INFO       : 'INFO',
	logging.DEBUG      : 'DEBUG',
}



class NoneDict (dict):
	def __getitem__ (self,name):
		return None
nonedict = NoneDict()

class value (object):
	location = os.path.normpath(sys.argv[0]) if sys.argv[0].startswith('/') else os.path.normpath(os.path.join(os.getcwd(),sys.argv[0]))

	@staticmethod
	def root (path):
		roots = value.location.split(os.sep)
		location = []
		for index in range(len(roots)-1,-1,-1):
			if roots[index] in ('lib','bin'):
				if index:
					location = roots[:index]
				break
		root = os.path.join(*location)
		paths = [
			os.path.normpath(os.path.join(os.path.join(os.sep,root,path))),
			os.path.normpath(os.path.expanduser(value.unquote(path))),
			os.path.normpath(os.path.join('/',path)),
			os.path.normpath(os.path.join('/','usr',path)),
		]
		return paths

	@staticmethod
	def integer (_):
		value = int(_)
		if value <= 0:
			raise TypeError('the value must be positive')
		return value

	@staticmethod
	def lowunquote (_):
		return _.strip().strip('\'"').lower()

	@staticmethod
	def unquote (_):
		return _.strip().strip('\'"')

	@staticmethod
	def quote (_):
		return "'%s'" % str(_)

	@staticmethod
	def nop (_):
		return _

	@staticmethod
	def boolean (_):
		return _.lower() in ('1','yes','on','enable','true')

	@staticmethod
	def methods (_):
		return _.upper().split()

	@staticmethod
	def list (_):
		return "'%s'" % ' '.join(_)

	@staticmethod
	def lower (_):
		return str(_).lower()

	@staticmethod
	def user (_):
		# XXX: incomplete
		try:
			pwd.getpwnam(_)
			# uid = answer[2]
		except KeyError:
			raise TypeError('user %s is not found on this system' % _)
		return _

	@staticmethod
	def folder(path):
		paths = value.root(path)
		options = [path for path in paths if os.path.exists(path)]
		if not options: raise TypeError('%s does not exists' % path)
		first = options[0]
		if not first: raise TypeError('%s does not exists' % first)
		return first

	@staticmethod
	def path (path):
		split = sys.argv[0].split('lib/exaproxy')
		if len(split) > 1:
			prefix = os.sep.join(split[:1])
			if prefix and path.startswith(prefix):
				path = path[len(prefix):]
		home = os.path.expanduser('~')
		if path.startswith(home):
			return "'~%s'" % path[len(home):]
		return "'%s'" % path

	@staticmethod
	def conf(path):
		first = value.folder(path)
		if not os.path.isfile(first): raise TypeError('%s is not a file' % path)
		return first

	@staticmethod
	def resolver(path):
		paths = value.root('etc/exaproxy/dns/resolv.conf')
		paths.append(os.path.normpath(os.path.join('/','etc','resolv.conf')))
		for resolver in paths:
			if os.path.exists(resolver):
				with open(resolver) as r:
					if 'nameserver' in (line.strip().split(None,1)[0].lower() for line in r.readlines()):
						return resolver
		raise TypeError('resolv.conf can not be found')

	@staticmethod
	def exe (path):
		first = value.conf(path)
		if not os.access(first, os.X_OK): raise TypeError('%s is not an executable' % first)
		return first

	# @staticmethod
	# def syslog (path):
	# 	path = value.unquote(path)
	# 	if path in ('stdout','stderr'):
	# 		return path
	# 	if path.startswith('host:'):
	# 		return path
	# 	return path

	@staticmethod
	def redirector (name):
		if name == 'url' or name.startswith('icap://'):
			return name
		raise TypeError('invalid redirector protocol %s, options are url or header' % name)

	@staticmethod
	def syslog_int (log):
		if log not in _syslog_name_value:
			raise TypeError('invalid log level %s' % log)
		return _syslog_name_value[log]

	@staticmethod
	def syslog_value (log):
		if log not in _syslog_name_value:
			raise TypeError('invalid log level %s' % log)
		return _syslog_name_value[log]

	@staticmethod
	def syslog_name (log):
		if log not in _syslog_value_name:
			raise TypeError('invalid log level %s' % log)
		return _syslog_value_name[log]

defaults = {
	'tcp4' : {
		'host'    : (value.unquote,value.quote,'127.0.0.1', 'the host the proxy listen on'),
		'port'    : (value.integer,value.nop,'3128',        'the port the proxy listen on'),
		'timeout' : (value.integer,value.nop,'5',           'time before we abandon inactive established connections'),
		'backlog' : (value.integer,value.nop,'200',         'when busy how many connection should the OS queue for us'),
		'listen'  : (value.boolean,value.lower,'true',      'should we listen for connections over IPv4'),
		'out'     : (value.boolean,value.lower,'true',      'allow connections to remote web servers over IPv4'),
	},
	'tcp6' : {
		'host'    : (value.unquote,value.quote,'::1',   'the host the proxy listen on'),
		'port'    : (value.integer,value.nop,'3128',    'the port the proxy listen on'),
		'timeout' : (value.integer,value.nop,'5',       'time before we abandon inactive established connections'),
		'backlog' : (value.integer,value.nop,'200',     'when busy how many connection should the OS queue for us'),
		'listen'  : (value.boolean,value.lower,'false', 'should we listen for connections over IPv6'),
		'out'     : (value.boolean,value.lower,'true',  'allow connections to remote web servers over IPv6'),
	},
	'redirector' : {
		'enable'  : (value.boolean,value.lower,'false',                         'use redirector programs to filter http request'),
		'program' : (value.exe,value.path,'etc/exaproxy/redirector/url-allow',  'the program used to know where to send request'),
		'minimum' : (value.integer,value.nop,'5',                               'minimum number of worker threads (forked program)'),
		'maximum' : (value.integer,value.nop,'25',                              'maximum number of worker threads (forked program)'),
#		'timeout' : (value.integer,value.nop,'1',                               'how long to wait for work before peforming background work'),
		'protocol': (value.redirector,value.quote,'url',                        'what protocol to use (url -> squid like / icap:://<uri> -> icap like)')
	},

	'http' : {
		'transparent'     : (value.boolean,value.lower,'false', 'do not reveal the presence of the proxy'),
		'forward'         : (value.lowunquote,value.quote,'',   'read client address from this header (normally x-forwarded-for)'),
		'allow-connect'   : (value.boolean,value.lower,'true',  'allow client to use CONNECT and https connections'),
		'extensions'      : (value.methods,value.list,'',       'allow new HTTP method (space separated)'),
		'proxied'         : (value.boolean,value.lower,'false', 'request is encapsulated with proxy protocol'),
	},
	'web' : {
		'enable'      : (value.boolean,value.lower,'true',             'enable the built-in webserver'),
		'host'        : (value.unquote,value.quote,'127.0.0.1',        'the address the web server listens on'),
		'port'        : (value.integer,value.nop,'8080',               'port the web server listens on'),
		'html'        : (value.folder,value.path,'etc/exaproxy/html',  'where internal proxy html pages are served from'),
		'connections' : (value.integer,value.nop,'100',                'the maximum number of web connections'),
	},
	'daemon' : {
		'identifier'  : (value.unquote,value.nop,'ExaProxy','a name for the log (to diferenciate multiple instances more easily)'),
		'pidfile'     : (value.unquote,value.quote,'',      'where to save the pid if we manage it'),
		'user'        : (value.user,value.quote,'nobody',   'user to run as'),
		'daemonize'   : (value.boolean,value.lower,'false', 'should we run in the background'),
		'reactor'     : (value.unquote,value.quote,'epoll', 'what event mechanism to use (select/epoll)'),
		'speed'       : (value.integer,value.nop,'2',       'when waiting for connection how long are we sleeping for'),
		'connections' : (value.integer,value.nop,'10240',   'the maximum number of proxy connections'),
	},
	'dns' : {
		'resolver'     : (value.resolver,value.path,'/etc/resolv.conf',       'resolver file'),
		'timeout'      : (value.integer,value.nop,'60',                       'how long to wait for DNS replies'),
		'retries'      : (value.integer,value.nop,'3',                        'how many times to retry sending requests'),
#		'force-ttl'    : (value.boolean,value.lower,'true',                   'do not use DNS ttl but the ttl value in this configuration'),
		'resolution'   : (value.integer,value.nop,'3',                        'group dns cache results '),
		'ttl'          : (value.integer,value.nop,'900',                      'amount of time (in seconds) we will cache dns results for - should be a multiple of dns.resolution'),
		'fqdn'         : (value.boolean,value.lower,'true',                   'only resolve FQDN (hostnames must have a dot'),
		'definitions'  : (value.folder,value.path,'etc/exaproxy/dns/types',   'location of file defining dns query types'),
	},
	'log' : {
		'enable'        : (value.boolean,value.lower,'true',               'enable traffic logging'),
		'level'         : (value.syslog_value,value.syslog_name,'ERROR', 'log message with at least the priority logging.<level>'),
		'destination'   : (value.unquote,value.quote,'stdout',             'where syslog should log'),
		'signal'        : (value.boolean,value.lower,'true',               'log messages from the signal subsystem'),
		'configuration' : (value.boolean,value.lower,'true',               'log messages from the configuration subsystem'),
		'supervisor'    : (value.boolean,value.lower,'true',               'log messages from the supervisor subsystem'),
		'daemon'        : (value.boolean,value.lower,'true',               'log messages from the daemon subsystem'),
		'server'        : (value.boolean,value.lower,'true',               'log messages from the server subsystem'),
		'client'        : (value.boolean,value.lower,'true',               'log messages from the client subsystem'),
		'manager'       : (value.boolean,value.lower,'true',               'log messages from the manager subsystem'),
		'worker'        : (value.boolean,value.lower,'true',               'log messages from the worker subsystem'),
		'download'      : (value.boolean,value.lower,'true',               'log messages from the download subsystem'),
		'http'          : (value.boolean,value.lower,'true',               'log messages from the http subsystem'),
		'header'        : (value.boolean,value.lower,'true',               'log messages from the header subsystem'),
		'resolver'      : (value.boolean,value.lower,'true',               'log messages from the dns subsystem'),
	},
	'usage' : {
		'enable'        : (value.boolean,value.lower,'false',              'enable traffic logging'),
		'destination'   : (value.unquote,value.quote,'stdout',              'where syslog should log'),
	},
	'profile' : {
		'enable'      : (value.boolean,value.lower,'false', 'enable profiling'),
		'destination' : (value.unquote,value.quote,'stdout', 'save profiling to file (instead of to the screen on exit)'),
	},
	'proxy' : {
		'version' : (value.nop,value.nop,'unknown',  'ExaProxy\'s version'),
	},
	# Here for internal use
	'debug' : {
		'memory' : (value.boolean,value.lower,'false','command line option --memory'),
		'pdb'    : (value.boolean,value.lower,'false','command line option --pdb'),
		'log'    : (value.boolean,value.lower,'false','command line option --debug'),
	},
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


def _configuration (conf):
	location = os.path.join(os.sep,*os.path.join(value.location.split(os.sep)))
	while location and location != '/':
		location, directory = os.path.split(location)
		if directory in ('lib','bin'):
			break

	_conf_paths = []
	if conf:
		_conf_paths.append(os.path.abspath(os.path.normpath(conf)))
	if location:
		_conf_paths.append(os.path.normpath(os.path.join(location,'etc','exaproxy','exaproxy.conf')))
	_conf_paths.append(os.path.normpath(os.path.join('/','etc','exaproxy','exaproxy.conf')))
	_conf_paths.append(os.path.normpath(os.path.join('/','usr','etc','exaproxy','exaproxy.conf')))

	configuration = Store()
	ini = ConfigParser.ConfigParser()

	ini_files = [path for path in _conf_paths if os.path.exists(path)]
	if ini_files:
		ini.read(ini_files[0])

	for section in defaults:
		default = defaults[section]

		for option in default:
			convert = default[option][0]
			try:
				proxy_section = 'exaproxy.%s' % section
				env_name = '%s.%s' % (proxy_section,option)
				rep_name = env_name.replace('.','_')

				if env_name in os.environ:
					conf = os.environ.get(env_name)
				elif rep_name in os.environ:
					conf = os.environ.get(rep_name)
				else:
					# raise and set the default
					conf = value.unquote(ini.get(proxy_section,option,nonedict))
					# name without an = or : in the configuration and no value
					if conf == None:
						conf = default[option][2]
			except (ConfigParser.NoSectionError,ConfigParser.NoOptionError):
				conf = default[option][2]
			try:
				configuration.setdefault(section,Store())[option] = convert(conf)
			except TypeError,error:
				raise ConfigurationError('invalid value for %s.%s : %s (%s)' % (section,option,conf,str(error)))

	return configuration

__configuration = None

def load (conf=None):
	global __configuration
	if __configuration:
		return __configuration
	if conf is None:
		raise RuntimeError('You can not have an import using load() before main() initialised it')
	__configuration = _configuration(conf)
	return __configuration

def default ():
	for section in sorted(defaults):
		for option in sorted(defaults[section]):
			values = defaults[section][option]
			default = "'%s'" % values[2] if values[1] in (value.list,value.path,value.quote,value.unquote) else values[2]
			yield 'exaproxy.%s.%s %s: %s. default (%s)' % (section,option,' '*(20-len(section)-len(option)),values[3],default)

def ini (diff=False):
	for section in sorted(__configuration):
		if section in ('proxy','debug'):
			continue
		header = '\n[exaproxy.%s]' % section
		for k in sorted(__configuration[section]):
			v = __configuration[section][k]
			if diff and defaults[section][k][0](defaults[section][k][2]) == v:
				continue
			if header:
				print header
				header = ''
			print '%s = %s' % (k,defaults[section][k][1](v))

def env (diff=False):
	print
	for section,values in __configuration.items():
		if section in ('proxy','debug'):
			continue
		for k,v in values.items():
			if diff and defaults[section][k][0](defaults[section][k][2]) == v:
				continue
			if defaults[section][k][1] == value.quote:
				print "exaproxy.%s.%s='%s'" % (section,k,v)
				continue
			print "exaproxy.%s.%s=%s" % (section,k,defaults[section][k][1](v))
