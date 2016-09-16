#!/usr/bin/env python
# encoding: utf-8
"""
setup.py

Created by Thomas Mangin on 2011-01-24.
Copyright (c) 2011-2012 Exa Networks. All rights reserved.
"""

import os
import sys
from distutils.core import setup
from distutils.util import get_platform
from setuptools.command.install import install
from setuptools.command.easy_install import chmod

try:
	version = None
	root = os.path.dirname(os.path.join(os.getcwd(),sys.argv[0]))
	with open(os.path.join(root,'lib/exaproxy/application.py'),'r') as stream:
		for line in stream:
			if line.startswith("version = '"):
				_,version,_ = line.split("'")
				break
	if version is None:
		raise Exception()
	if False in [ _.isdigit() for _ in version.split('.')]:
		raise Exception()
	print 'exaproxy version', version
except Exception,e:
	print "can not extract exaproxy version"
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
		e = []
		for f in fs:
			e.append(os.path.join(l,f))
		etcs.append((l,e))
	return etcs

def files ():
	r = []
	if 'linux' in sys.platform:
		r.append(('/usr/lib/systemd/system',['etc/systemd/exaproxy.service',]))
	r.extend(configuration('etc/exaproxy'))
	return r

class custom_install (install):
	def run (self):
		install.run(self)

		if not self.dry_run:
			for names in ( names for section,names in files() if section == 'etc/exaproxy/redirector'):
				for name in names:
					location = os.path.join(self.install_data,name)
					chmod(location, 0755) # the 0 make the value octal
			install.run(self)



setup(name='exaproxy',
	version=version,
	description='non-caching http/https proxy',
	long_description="ExaProxy is a forward (or reverse) non-caching proxy. It can be used transparently and/or to rewrite HTTP requests.",
	author='Thomas Mangin, David Farrar',
	author_email='thomas.mangin@exa-networks.co.uk, david.farrar@exa-networks.co.uk',
	url='https://github.com/Exa-Networks/exaproxy',
	license="BSD",
	platforms=[get_platform(),],
	package_dir = {'': 'lib'},
	packages=packages('lib'),
	scripts=['scripts/exaproxy',],
#	entry_points = {'console_scripts': ['exaproxy = exaproxy.application:main',]},
	download_url='https://codeload.github.com/Exa-Networks/exaproxy/tar.gz/%s' % version,
	data_files=files(),
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
	cmdclass={'install': custom_install},
)

