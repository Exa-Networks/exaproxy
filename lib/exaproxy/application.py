#!/usr/bin/env python
# encoding: utf-8
"""
proxy.py

Created by Thomas Mangin on 2011-11-29.
Copyright (c) 2011 Exa Networks. All rights reserved.
"""

import sys
# XXX: not good to have to import syslog here
import syslog

from exaproxy.supervisor import Supervisor
from exaproxy.util.logger import logger
from exaproxy.configuration import ConfigurationError,load,ini,env,default

def version_warning ():
	sys.stdout.write('\n')
	sys.stdout.write('************ WARNING *** WARNING *** WARNING *** WARNING *********\n')
	sys.stdout.write('*                                                                *\n')
	sys.stdout.write('* This program is only supported on Python version 2.6 or 2.7.   *\n')
	sys.stdout.write('* Please consider upgrading to the latest 2.x stable realease.   *\n')
	sys.stdout.write('*                                                                *\n')
	sys.stdout.write('************ WARNING *** WARNING *** WARNING *** WARNING *********\n')
	sys.stdout.write('\n')

def help ():
	sys.stdout.write('usage:\n exaproxy [-h,--help] [-i,--ini] [-e,--env]\n')
	sys.stdout.write('\n')
	sys.stdout.write(' -h, --help : print this configuration help\n')
	sys.stdout.write(' -i, --ini  : print out the configuration on ini format\n')
	sys.stdout.write(' -e, --env  : print out the configuration on env format\n')
	sys.stdout.write('\n')
	sys.stdout.write('exaproxy will automatically look for its configuration file\n')
	sys.stdout.write(' - if the program was untar, within its etc/exaproxy folder\n')
	sys.stdout.write(' - in /etc/exaproxy/exaproxy.conf\n')
	sys.stdout.write('every configuration value has a built-in default\n')
	sys.stdout.write('\n')
	sys.stdout.write('individual configuration options can be set using environment variables, such as :\n')
	sys.stdout.write('> env exaproxy.redirector.program=etc/exaproxy/redirector/deny ./sbin/exaproxy\n')
	sys.stdout.write('or \n')
	sys.stdout.write('> env exaproxy_redirector_program=etc/exaproxy/redirector/deny ./sbin/exaproxy\n')
	sys.stdout.write('or \n')
	sys.stdout.write('> export exaproxy_redirector_program=etc/exaproxy/redirector/deny\n')
	sys.stdout.write('> ./sbin/exaproxy\n')
	sys.stdout.write('\n')
	sys.stdout.write('multiple environment values can be set\n')
	sys.stdout.write('\n')
	sys.stdout.write('shortcut to turn all possible debugging on\n')
	sys.stdout.write('env DEBUG_ALL=1 ./sbin/exaproxy\n')
	sys.stdout.write('\n')
	sys.stdout.write('valid configuration options are :\n')
	sys.stdout.write('\n')
	for line in default():
			sys.stdout.write(' - %s\n' % line)
	sys.stdout.write('\n')

def main ():
	main = int(sys.version[0])
	secondary = int(sys.version[2])

	if main != 2 or secondary < 4:
		sys.exit('This program can not work (is not tested) with your python version (< 2.4 or >= 3.0)')

	if main == 2 and secondary == 4:
		version_warning()

#	if len(sys.argv) < 2:
#		help()
#		sys.exit(0)

	for arg in sys.argv[1:]:
		if arg in ['--',]:
			break
		if arg in ['-h','--help']:
			help()
			sys.exit(0)
		if arg in ['-i','--ini']:
			ini()
			sys.exit(0)
		if arg in ['-e','--env']:
			env()
			sys.exit(0)
	
	Supervisor().run()
	sys.exit(0)

if __name__ == '__main__':
	try:
		configuration = load()
	except ConfigurationError,e:
		print >> sys.stderr, 'configuration issue,', str(e)
		sys.exit(1)

	_all = os.environ.get('DEBUG_ALL','0') != '0'
	for section,value in configuration.logger.items():
		if section == 'level':
			if _all:
				logger.level = syslog.LOG_DEBUG
			elif section != 'destination':
				logger.level = value
		else:
			logger.status[section] = value or _all

	logger.syslog(configuration.logger.destination)

	if not configuration.profile.enabled:
		main()
		sys.exit(0)

	try:
		import cProfile as profile
	except:
		import profile

	if not configuration.profile.destination:
		profile.run('main()')
		sys.exit(0)

	notice = ''
	if os.path.isdir(configuration.profile.destination):
		notice = 'profile can not use this filename as outpout, it is not a directory (%s)' % profiled
	if os.path.exists(configuration.profile.destination):
		notice = 'profile can not use this filename as outpout, it already exists (%s)' % profiled

	if not notice:
		logger.debug('supervisor','profiling ....')
		profile.run('main()',filename=configuration.profile.destination)
	else:
		logger.debug('supervisor',"-"*len(notice))
		logger.debug('supervisor',notice)
		logger.debug('supervisor',"-"*len(notice))
		main()
	sys.exit(0)
