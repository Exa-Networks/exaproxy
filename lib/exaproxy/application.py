# encoding: utf-8
"""
proxy.py

Created by Thomas Mangin on 2011-11-29.
Copyright (c) 2011-2013  Exa Networks. All rights reserved.
"""

import os
import sys

from exaproxy.configuration import default,value,string

version = '1.2.1'

def version_warning ():
	sys.stdout.write('\n')
	sys.stdout.write('************ WARNING *** WARNING *** WARNING *** WARNING *********\n')
	sys.stdout.write('*                                                                *\n')
	sys.stdout.write('* This program is only supported on Python version 2.6 or 2.7.   *\n')
	sys.stdout.write('* Please consider upgrading to the latest 2.x stable realease.   *\n')
	sys.stdout.write('*                                                                *\n')
	sys.stdout.write('************ WARNING *** WARNING *** WARNING *** WARNING *********\n')
	sys.stdout.write('\n')

def usage ():
	sys.stdout.write('usage:\n exaproxy [options]\n')
	sys.stdout.write('\n')
	sys.stdout.write('  -h, --help      : this help\n')
	sys.stdout.write('  -c, --conf-file : configuration file to use (ini format)\n')
	sys.stdout.write('  -i, -fi, --ini  : display the configuration using the ini format\n')
	sys.stdout.write('  -e, -fe, --env  : display the configuration using the env format\n')
	sys.stdout.write(' -di, --diff-ini  : display non-default configurations values using the ini format\n')
	sys.stdout.write(' -de, --diff-env  : display non-default configurations values using the env format\n')
	sys.stdout.write('  -d, --debug     : shortcut to turn on all subsystems debugging to LOG_DEBUG\n')
	sys.stdout.write('  -p, --pdb       : start the python debugger on serious logging and on SIGTERM\n')
	sys.stdout.write('  -m, --memory    : display memory usage information on exit\n')

	sys.stdout.write('\n')
	sys.stdout.write('ExaProxy will automatically look for its configuration file (in windows ini format)\n')
	sys.stdout.write(' - 1 : in      etc/exaproxy/exaproxy.conf (relative position within the extracted tgz file)\n')
	sys.stdout.write(' - 2 : in     /etc/exaproxy/exaproxy.conf\n')
	sys.stdout.write(' - 3 : in /usr/etc/exaproxy/exaproxy.conf\n')
	sys.stdout.write('\n')
	sys.stdout.write('You can generate the configuration file using the -i, or -fi, option')
	sys.stdout.write('Every configuration value has a sensible built-in default\n')
	sys.stdout.write('\n')
	sys.stdout.write('Individual configuration options can be set using environment variables, such as :\n')
	sys.stdout.write('   > env exaproxy.dns.timeout=20 ./sbin/exaproxy\n')
	sys.stdout.write('or > env exaproxy_dns_timeout=20 ./sbin/exaproxy\n')
	sys.stdout.write('or > export exaproxy_dns_timeout=20; ./sbin/exaproxy\n')
	sys.stdout.write('\n')
	sys.stdout.write('Multiple environment values can be set\n')
	sys.stdout.write('and the order of preference is :\n')
	sys.stdout.write(' - 1 : command line env value using dot separated notation\n')
	sys.stdout.write(' - 2 : exported value from the shell using dot separated notation\n')
	sys.stdout.write(' - 3 : command line env value using underscore separated notation\n')
	sys.stdout.write(' - 4 : exported value from the shell using underscore separated notation\n')
	sys.stdout.write(' - 5 : the value in the ini configuration file\n')
	sys.stdout.write('\n')
	sys.stdout.write('The following UNIX signal are acted on :\n')
	sys.stdout.write(' - SIGUSR1  : decrease the maximum number of processes\n')
	sys.stdout.write(' - SIGUSR2  : increase the mininum number of processes\n')
	sys.stdout.write(' - SIGTTOU  : stop listening for new proxy connections\n')
	sys.stdout.write(' - SIGTTIN  : start listening for new proxy connections\n')
	sys.stdout.write(' - SIGQUIT  : stop listening and exit when exiting connections are all closed\n')
	sys.stdout.write(' - SIGTERM  : terminate the program immediatly (SIGINT too atm)\n')
	sys.stdout.write('\n')
	sys.stdout.write('Valid configuration options are :\n')
	sys.stdout.write('\n')
	for line in default():
			sys.stdout.write(' - %s\n' % line)
	sys.stdout.write('\n')

def show_version (version):
	print 'exaproxy %s' % version

def __exit(memory,code):
	if memory:
		from exaproxy.leak import objgraph
		print "memory utilisation"
		print
		print objgraph.show_most_common_types(limit=20)
		print
		print
		print "generating memory utilisation graph"
		print
		obj = objgraph.by_type('Supervisor')
		objgraph.show_backrefs([obj], max_depth=10)
	sys.exit(code)

def main ():
	primary = int(sys.version[0])
	secondary = int(sys.version[2])

	if primary != 2 or secondary < 4:
		sys.exit('This program can not work (is not tested) with your python version (< 2.4 or >= 3.0)')

	if primary == 2 and secondary == 4:
		version_warning()

	from exaproxy.configuration import ConfigurationError,load,ini,env

	followup = ''
	arguments = {
		'configuration' : '',
	}

	for arg in sys.argv[1:]:
		if followup:
			arguments[followup] = arg
			followup = ''
			continue
		if arg in ['-c','--conf-file']:
			followup = 'configuration'

	defaults = {
		'tcp4' : {
			'host'    : (value.unquote,string.quote,'127.0.0.1', 'the host the proxy listen on'),
			'port'    : (value.integer,string.nop,'3128',        'the port the proxy listen on'),
			'timeout' : (value.integer,string.nop,'5',           'time before we abandon inactive established connections'),
			'backlog' : (value.integer,string.nop,'200',         'when busy how many connection should the OS queue for us'),
			'listen'  : (value.boolean,string.lower,'true',      'should we listen for connections over IPv4'),
			'out'     : (value.boolean,string.lower,'true',      'allow connections to remote web servers over IPv4'),
			'bind'    : (value.unquote,string.quote,'0.0.0.0',   'which ipv4 to use when creating outbound connection'),
		},
		'tcp6' : {
			'host'    : (value.unquote,string.quote,'::1',   'the host the proxy listen on'),
			'port'    : (value.integer,string.nop,'3128',    'the port the proxy listen on'),
			'timeout' : (value.integer,string.nop,'5',       'time before we abandon inactive established connections'),
			'backlog' : (value.integer,string.nop,'200',     'when busy how many connection should the OS queue for us'),
			'listen'  : (value.boolean,string.lower,'false', 'should we listen for connections over IPv6'),
			'out'     : (value.boolean,string.lower,'true',  'allow connections to remote web servers over IPv6'),
			'bind'    : (value.unquote,string.quote,'::',    'which ipv6 to use when creating outbound connection'),
		},
		'redirector' : {
			'enable'  : (value.boolean,string.lower,'false',                         'use redirector programs to filter http request'),
			'program' : (value.exe,string.path,'etc/exaproxy/redirector/url-allow',  'the program used to know where to send request'),
			'minimum' : (value.integer,string.nop,'5',                               'minimum number of worker threads (forked program)'),
			'maximum' : (value.integer,string.nop,'25',                              'maximum number of worker threads (forked program)'),
			'protocol': (value.redirector,string.quote,'url',                        'what protocol to use (url -> squid like / icap:://<uri> -> icap like)')
		},
		'http' : {
			'idle-connect'    : (value.integer,string.nop,'300',     'time before we abandon new inactive http client connections (0: unlimited)'),
			'connections'     : (value.integer,string.nop,'32768',   'the maximum number of proxy connections'),
			'transparent'     : (value.boolean,string.lower,'false', 'do not reveal the presence of the proxy'),
			'forward'         : (value.lowunquote,string.quote,'',   'read client address from this header (normally x-forwarded-for)'),
			'mask'            : (value.boolean,string.lower,'false', 'hide client address by removing the header specified in exaproxy.http.forward'),
			'connect'         : (value.boolean,string.lower,'true',  'allow client to use CONNECT and https connections'),
			'expect'          : (value.boolean,string.lower,'false', 'block messages with EXPECT headers with a 417'),
			'extensions'      : (value.methods,string.list,'',       'allow new HTTP method (space separated)'),
			'proxied'         : (value.boolean,string.lower,'false', 'request is encapsulated with haproxy proxy protocol'),
			'header-size'     : (value.integer,string.nop,'65536',   'maximum size in bytes for HTTP headers (0 : unlimited)'),
		},
		'passthrough' : {
			'enable'          : (value.boolean,string.lower,'false',             'enable the passthrough server'),
			'host'            : (value.unquote,string.quote,'127.0.0.1',        'the address the passthrough server listens on'),
			'ipv6'            : (value.unquote,string.quote,'::',               'the ipv6 address the passthrough server listens on'),
			'port'            : (value.integer,string.nop,'8000',               'port the passthrough server listens on'),
			'idle-connect'    : (value.integer,string.nop,'300',     'time before we abandon new inactive passthrough client connections (0: unlimited)'),
			'connections'     : (value.integer,string.nop,'32768',   'the maximum number of passthrough connections'),
			'proxied'         : (value.boolean,string.lower,'false', 'request is encapsulated with haproxy proxy protocol'),
		},
		'icap' : {
			'enable'          : (value.boolean,string.lower,'false',             'enable the icap server'),
			'host'            : (value.unquote,string.quote,'127.0.0.1',        'the address the icap server listens on'),
			'ipv6'            : (value.unquote,string.quote,'::',               'the ipv6 address the icap server listens on'),
			'port'            : (value.integer,string.nop,'1344',               'port the icap server listens on'),
			'idle-connect'    : (value.integer,string.nop,'300',     'time before we abandon new inactive icap client connections (0: unlimited)'),
			'connections'     : (value.integer,string.nop,'32768',   'the maximum number of icap connections'),
			'proxied'         : (value.boolean,string.lower,'false', 'request is encapsulated with haproxy proxy protocol'),
			'header-size'     : (value.integer,string.nop,'65536',   'maximum size in bytes for ICAP headers (0 : unlimited)'),
		},
		'tls' : {
			'enable'          : (value.boolean,string.lower,'false',             'enable the TLS server'),
			'host'            : (value.unquote,string.quote,'127.0.0.1',        'the address the TLS server listens on'),
			'ipv6'            : (value.unquote,string.quote,'::',               'the ipv6 address the TLS server listens on'),
			'port'            : (value.integer,string.nop,'443',               'port the TLS server listens on'),
			'idle-connect'    : (value.integer,string.nop,'300',     'time before we abandon new inactive TLS client connections (0: unlimited)'),
			'connections'     : (value.integer,string.nop,'32768',   'the maximum number of TLS connections'),
			'proxied'         : (value.boolean,string.lower,'false', 'request is encapsulated with haproxy proxy protocol'),
			'header-size'     : (value.integer,string.nop,'65536',   'maximum size in bytes for TLS headers (0 : unlimited)'),
		},
		'web' : {
			'enable'      : (value.boolean,string.lower,'true',             'enable the built-in webserver'),
			'host'        : (value.unquote,string.quote,'127.0.0.1',        'the address the web server listens on'),
			'port'        : (value.integer,string.nop,'8080',               'port the web server listens on'),
			'html'        : (value.folder,string.path,'etc/exaproxy/html',  'where internal proxy html pages are served from'),
			'connections' : (value.integer,string.nop,'100',                'the maximum number of web connections'),
			'debug'       : (value.boolean,string.lower,'false',            'allow to debug the program via the web client (do not use in production)'),
		},
		'daemon' : {
			'identifier'  : (value.unquote,string.nop,'ExaProxy','a name for the log (to diferenciate multiple instances more easily)'),
			'pidfile'     : (value.unquote,string.quote,'',      'where to save the pid if we manage it'),
			'user'        : (value.user,string.quote,'nobody',   'user to run as'),
			'daemonize'   : (value.boolean,string.lower,'false', 'should we run in the background'),
			'reactor'     : (value.unquote,string.quote,'best', 'event polling mechanism to use (select/epoll/kqueue/best)'),
			'speed'       : (value.integer,string.nop,'2',       'sleep duration when waiting for connection'),
			'poll-interfaces' : (value.boolean,string.lower,'true',  'periodically poll for local addresses the proxy should not connect to'),
		},
		'security' : {
			'local'       : (value.services,string.services,   '',              'ip:port for allowed services (*:80 or 127.0.0.1:* allowed)'),
			'connect'     : (value.ports,string.list,          '443 981 7000',  'ports allowed with CONNECT'),
		},
		'dns' : {
			'resolver'     : (value.resolver,string.path,'/etc/resolv.conf',       'resolver file'),
			'timeout'      : (value.integer,string.nop,'2',                        'how long to wait for DNS replies before retrying'),
			'retries'      : (value.integer,string.nop,'10',                       'how many times to retry sending requests'),
			'ttl'          : (value.integer,string.nop,'900',                      'amount of time (in seconds) we will cache dns results for'),
			'fqdn'         : (value.boolean,string.lower,'true',                   'only resolve FQDN (hostnames must have a dot'),
			'definitions'  : (value.folder,string.path,'etc/exaproxy/dns/types',   'location of file defining dns query types'),
		},
		'log' : {
			'enable'        : (value.boolean,string.lower,'true',               'enable traffic logging'),
			'level'         : (value.syslog,string.syslog,'ERROR',              'log message with at least the priority logging.<level>'),
			'destination'   : (value.unquote,string.quote,'stdout',             'where syslog should log'),
			'signal'        : (value.boolean,string.lower,'true',               'log messages from the signal subsystem'),
			'configuration' : (value.boolean,string.lower,'true',               'log messages from the configuration subsystem'),
			'supervisor'    : (value.boolean,string.lower,'true',               'log messages from the supervisor subsystem'),
			'daemon'        : (value.boolean,string.lower,'true',               'log messages from the daemon subsystem'),
			'server'        : (value.boolean,string.lower,'true',               'log messages from the server subsystem'),
			'client'        : (value.boolean,string.lower,'true',               'log messages from the client subsystem'),
			'manager'       : (value.boolean,string.lower,'true',               'log messages from the manager subsystem'),
			'worker'        : (value.boolean,string.lower,'true',               'log messages from the worker subsystem'),
			'download'      : (value.boolean,string.lower,'true',               'log messages from the download subsystem'),
			'http'          : (value.boolean,string.lower,'true',               'log messages from the http subsystem'),
			'header'        : (value.boolean,string.lower,'true',               'log messages from the header subsystem'),
			'resolver'      : (value.boolean,string.lower,'true',               'log messages from the dns subsystem'),
			'web'           : (value.boolean,string.lower,'true',               'log messages from the web subsystem'),
		},
		'usage' : {
			'enable'        : (value.boolean,string.lower,'false',              'enable traffic logging'),
			'destination'   : (value.unquote,string.quote,'stdout',              'where syslog should log'),
		},
		'profile' : {
			'enable'      : (value.boolean,string.lower,'false', 'enable profiling'),
			'destination' : (value.unquote,string.quote,'stdout', 'save profiling to file (instead of to the screen on exit)'),
		},
		'proxy' : {
			'version' : (value.nop,string.nop,version,  'ExaProxy\'s version'),
		},
		# Here for internal use
		'debug' : {
			'memory' : (value.boolean,string.lower,'false','command line option --memory'),
			'pdb'    : (value.boolean,string.lower,'false','command line option --pdb'),
			'log'    : (value.boolean,string.lower,'false','command line option --debug'),
		},
	}

	try:
		configuration = load('exaproxy',defaults,arguments['configuration'])
	except ConfigurationError,e:
		print >> sys.stderr, 'configuration issue,', str(e)
		sys.exit(1)

	configuration.proxy.version = version

	from exaproxy.util.log.logger import Logger
	log = Logger('supervisor', configuration.log.supervisor)

	for arg in sys.argv[1:]:
		if arg in ['--',]:
			break
		if arg in ['-h','--help']:
			usage()
			sys.exit(0)
		if arg in ['-i','-fi','--ini']:
			ini()
			sys.exit(0)
		if arg in ['-e','-fe','--env']:
			env()
			sys.exit(0)
		if arg in ['-di','--diff-ini']:
			ini(True)
			sys.exit(0)
		if arg in ['-de','--diff-env']:
			env(True)
			sys.exit(0)
		if arg in ['-v','--version']:
			show_version(version)
			sys.exit(0)
		if arg in ['-d','--debug']:
			configuration.debug.log = True
			configuration.web.debug = True
		if arg in ['-p','--pdb']:
			# The following may fail on old version of python (but is required for debug.py)
			os.environ['PDB'] = 'true'
			configuration.debug.pdb = True
		if arg in ['-m','--memory']:
			configuration.debug.memory = True

	from exaproxy.supervisor import Supervisor

	if not configuration.profile.enable:
		Supervisor(configuration).run()
		__exit(configuration.debug.memory,0)

	try:
		import cProfile as profile
	except:
		import profile

	if not configuration.profile.destination or configuration.profile.destination == 'stdout':
		profile.run('Supervisor().run()')
		__exit(configuration.debug.memory,0)

	notice = ''
	profiled = configuration.profile.destination
	if os.path.isdir(profiled):
		notice = 'profile can not use this filename as outpout, it is not a directory (%s)' % profiled
	if os.path.exists(configuration.profile.destination):
		notice = 'profile can not use this filename as outpout, it already exists (%s)' % profiled

	if not notice:
		log.debug('profiling ....')
		profile.run('main()',filename=configuration.profile.destination)
	else:
		log.debug("-"*len(notice))
		log.debug(notice)
		log.debug("-"*len(notice))
		main()
	__exit(configuration.debug.memory,0)

if __name__ == '__main__':
	main()
