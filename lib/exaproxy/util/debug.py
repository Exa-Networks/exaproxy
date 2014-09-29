# encoding: utf-8
"""
debug.py

Created by Thomas Mangin on 2011-11-29.
Copyright (c) 2011-2013  Exa Networks. All rights reserved.
"""

import os
import sys

import traceback

from exaproxy.util.log.history import History


def bug_report (exc_type, value, trace):
	print >> sys.stderr, ''
	print >> sys.stderr, ''
	print >> sys.stderr, '-'*80
	print >> sys.stderr, '-- Please provide the information below on :'
	print >> sys.stderr, '-- http://code.google.com/p/exaproxy/issues/entry'
	print >> sys.stderr, '-'*80
	print >> sys.stderr, ''
	print >> sys.stderr, ''
	print >> sys.stderr, '-- Version'
	print >> sys.stderr, ''
	print >> sys.stderr, sys.version
	print >> sys.stderr, ''
	print >> sys.stderr, ''
	print >> sys.stderr, '-- Logging History'
	print >> sys.stderr, ''
	print >> sys.stderr, ''
	for line in History().formated():
		print >> sys.stderr, line
	print >> sys.stderr, ''
	print >> sys.stderr, ''
	print >> sys.stderr, '-- Traceback'
	print >> sys.stderr, ''
	print >> sys.stderr, ''
	traceback.print_exception(exc_type,value,trace)
	print >> sys.stderr, ''
	print >> sys.stderr, ''
	print >> sys.stderr, '-'*80
	print >> sys.stderr, '-- Please provide the information above on :'
	print >> sys.stderr, '-- http://code.google.com/p/exaproxy/issues/entry'
	print >> sys.stderr, '-'*80
	print >> sys.stderr, ''
	print >> sys.stderr, ''

	#print >> sys.stderr, 'the program failed with message :', value

def intercept (exc_type, value, trace):
	interactive = os.environ.get('PDB',None)

	if interactive in ['0','']:
		# PDB was set to 0 or '' which is undocumented, and we do nothing
		pass
	else:
		bug_report(exc_type, value, trace)
		if interactive == 'true':
			import pdb
			pdb.pm()

sys.excepthook = intercept

if sys.argv:
	del sys.argv[0]
	__file__ = os.path.abspath(sys.argv[0])
	__name__ = '__main__'
	execfile(sys.argv[0])
