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
	sys.stdout.write('* This program SHOULD work with your python version (2.4).       *\n')
	sys.stdout.write('* No tests have been performed. Consider python 2.4 unsupported  *\n')
	sys.stdout.write('* Please consider upgrading to the latest 2.x stable realease.   *\n')
	sys.stdout.write('************ WARNING *** WARNING *** WARNING *** WARNING *********\n')
	sys.stdout.write('\n')

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
				logger.supervisor('profiling ....')
				profile.run('main()',filename=profiled)
			else:
				logger.supervisor("-"*len(notice))
				logger.supervisor(notice)
				logger.supervisor("-"*len(notice))
				main()
	sys.exit(0)
