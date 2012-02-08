#!/usr/bin/env python
# encoding: utf-8
"""
proxy.py

Created by Thomas Mangin on 2011-11-29.
Copyright (c) 2011 Exa Networks. All rights reserved.
"""

import sys

from exaproxy.supervisor import Supervisor
from exaproxy.util.logger import logger
from exaproxy.configuration import configuration

def version_warning ():
	sys.stdout.write('\n')
	sys.stdout.write('************ WARNING *** WARNING *** WARNING *** WARNING *********\n')
	sys.stdout.write('*                                                                *\n')
	sys.stdout.write('* This program is only supported on Python version 2.6 or 2.7.   *\n')
	sys.stdout.write('* Please consider upgrading to the latest 2.x stable realease.   *\n')
	sys.stdout.write('*                                                                *\n')
	sys.stdout.write('************ WARNING *** WARNING *** WARNING *** WARNING *********\n')
	sys.stdout.write('\n')

def resolv_warning ():
	sys.stdout.write('\n')
	sys.stdout.write('************ WARNING *** WARNING *** WARNING *** WARNING *********\n')
	sys.stdout.write('*                                                                *\n')
	sys.stdout.write('* ExaProxy could not find a valid resolv.conf file               *\n')
	sys.stdout.write('* Please tell us where you want us to look for your nameserver   *\n')
	sys.stdout.write('* in %-59s *\n' % configuration.internal_resolv)
	sys.stdout.write('* using the format :                                             *\n')
	sys.stdout.write('* namserver <ip address>                                         *\n')
	sys.stdout.write('*                                                                *\n')
	sys.stdout.write('************ WARNING *** WARNING *** WARNING *** WARNING *********\n')
	sys.stdout.write('\n')


def program_warning ():
	sys.stdout.write('The parameter passed is not a valid executable "%s" \n' % sys.argv[1])

def help ():
	sys.stdout.write('\n')
	sys.stdout.write('*******************************************************************************\n')
	sys.stdout.write('set the following environment values to gather information and report bugs\n')
	sys.stdout.write('\n')
	sys.stdout.write('DEBUG_ALL : debug everything\n')
	sys.stdout.write('\n')
	sys.stdout.write('PROFILE : (1,true,on,yes,enable) profiling info on exist\n')
	sys.stdout.write('          use a filename to dump the outpout in a file\n')
	sys.stdout.write('          IMPORTANT : exabpg will not overwrite existing files\n')
	sys.stdout.write('\n')
	sys.stdout.write('PDB : on program fault, start pdb the python interactive debugger\n')
	sys.stdout.write('\n')
	sys.stdout.write('USER : the user the program should try to use if run by root (default: nobody)\n')
	sys.stdout.write('PID : the file in which the pid of the program should be stored\n')
	sys.stdout.write('SYSLOG: no value for local syslog, a file name (which will auto-rotate) or host:<host> for remote syslog\n')
	sys.stdout.write('DAEMONIZE: detach and send the program in the background\n')
	sys.stdout.write('\n')
	sys.stdout.write('HOST : IP address the main service will listen on (default: 127.0.0.1)\n')
	sys.stdout.write('PORT : Port the main service will listen on (default: 31280)\n')
	sys.stdout.write('WEB: Port that the admin interface will listen on (default: 8080)\n')
	sys.stdout.write('TIMEOUT : Timeout for TCP connections in seconds (default: 5)\n')
	sys.stdout.write('BACKLOG: Number of unaccepted connections to be queued on the listening socket (default: 200)\n')
	sys.stdout.write('\n')
	sys.stdout.write('CONNECT: Allow users to CONNECT to an arbitrary destination (default: off)\n')
	sys.stdout.write('XFF: Identify the client by the address stored in a trusted X-Forwarded-For header rather than the peer IP (default: off)\n')
	sys.stdout.write('RESOLV: Use an alternate resolv.conf file  (default: /etc/resolv.conf)\n')
	sys.stdout.write('\n')
	sys.stdout.write('MIN_WORKERS: Mimimum number of classifier processes to spawn (default: 5)\n')
	sys.stdout.write('MAX_WORKERS: Maximum number of classifier processes to spawn (default: 25)\n')
	sys.stdout.write('WORKER_TIMEOUT: Maximum amount of uninterrupted time in seconds that a classifier thread will block while waiting for work (default: 5)\n')
	sys.stdout.write('SPEED: Maximum amount of uninterrupted time in seconds that the server will spend waiting on IO rather than managing resources (default: 2)\n')
	sys.stdout.write('\n')
	sys.stdout.write('For example :\n')
	sys.stdout.write('> env PDB=1 PROFILE=~/profile.log DEBUG_ALL=1 \\\n')
	sys.stdout.write('     USER=wheel SYSLOG=host:127.0.0.1 DAEMONIZE= PID=/var/run/exabpg.pid \\\n')
	sys.stdout.write('     ./bin/exaproxy ./etc/proxy/configuration.txt\n')
	sys.stdout.write('*******************************************************************************\n')
	sys.stdout.write('\n')
	sys.stdout.write('usage:\n exaproxy <script>\n')

def main ():
	main = int(sys.version[0])
	secondary = int(sys.version[2])

	if main != 2 or secondary < 4:
		sys.exit('This program can not work (is not tested) with your python version (< 2.4 or >= 3.0)')

	if main == 2 and secondary == 4:
		version_warning()

	if len(sys.argv) < 2:
		help()
		sys.exit(0)

	for arg in sys.argv[1:]:
		if arg in ['--',]:
			break
		if arg in ['-h','--help']:
			help()
			sys.exit(0)
	
	Supervisor().run()
	sys.exit(0)

if __name__ == '__main__':
	if not configuration.RESOLV:
		resolv_warning()
		sys.exit(1)

	if not configuration.PROGRAM:
		program_warning()
		sys.exit(1)

	logger.info('main','starting %s' % sys.argv[0])
	logger.info('main',sys.version.replace(os.linesep,' '))
	profiled = configuration.PROFILE
	if profiled == '0':
		main()
	else:
		try:
			import cProfile as profile
		except:
			import profile
		if profiled.lower() in ['1','true','yes','on','enable']:
			profile.run('main()')
		else:
			notice = ''
			if os.path.isdir(profiled):
				notice = 'profile can not use this filename as outpout, it is not a directory (%s)' % profiled
			if os.path.exists(profiled):
				notice = 'profile can not use this filename as outpout, it already exists (%s)' % profiled

			if not notice:
				logger.debug('supervisor','profiling ....')
				profile.run('main()',filename=profiled)
			else:
				logger.debug('supervisor',"-"*len(notice))
				logger.debug('supervisor',notice)
				logger.debug('supervisor',"-"*len(notice))
				main()
	sys.exit(0)
