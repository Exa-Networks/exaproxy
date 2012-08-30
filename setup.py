#!/usr/bin/env python
# encoding: utf-8
"""
setup.py

Created by Thomas Mangin on 2011-01-24.
Copyright (c) 2009-2012 Exa Networks. All rights reserved.
"""

import os
import sys
import glob
from distutils.core import setup
from distutils.util import get_platform

try:
	f = open('.hgtags','r')
	version = f.readlines()[-1].split(' ')[-1].strip()
	f.close()
except Exception,e:
	print "can not find the hgtags file in the repository"
	sys.exit(1)

def packages (lib):
	def dirs (*path):
		for location,_,_ in os.walk(os.path.join(*path)):
			yield location
	def modules (lib):
		return os.walk(lib).next()[1]
	r = []
	for module in modules(lib):
		for d in dirs(lib,module):
			r.append(d.replace('/','.').replace('\\','.')[len(lib)+1:])
	return r

def configuration (etc):
	etcs = []
	for l,d,fs in os.walk(etc):
		if not d:
			for f in fs:
				etcs.append(os.path.join(l,f))
	return etcs

setup(name='exaproxy',
	version=version,
	description='filtering proxy',
	long_description="ExaProxy was developed to be a transparent proxy, and can be used without client side configuration. Thanks to its url rewriting features, compatible with SQUID rewriters, it can as well be used as reverse proxy where complex URL rewriting are required.",
	author='Thomas Mangin, David Farrar',
	author_email='thomas.mangin@exa-networks.co.uk, david.farrar@exa-networks.co.uk',
	url='http://code.google.com/p/exaproxy/',
	license="BSD",
	platforms=[get_platform(),],
	package_dir = {'': 'lib'},
	packages=packages('lib'),
	scripts=['sbin/exaproxy',],
	download_url='http://exaproxy.googlecode.com/files/exaproxy-%s.tgz' % version,
	data_files=[
		('etc/exaproxy',configuration('etc/exaproxy')),
		('usr/lib/systemd/system',configuration('etc/systemd')),
	],
	classifiers=[
		'Development Status :: 4 - Beta',
		'Environment :: Console',
		'Intended Audience :: System Administrators',
		'License :: OSI Approved :: BSD License',
		'Operating System :: POSIX',
		'Operating System :: MacOS :: MacOS X',
		'Programming Language :: Python',
		'Topic :: Internet :: WWW/HTTP',
	],
)
