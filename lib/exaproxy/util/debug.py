# encoding: utf-8
"""
debug.py

Created by Thomas Mangin on 2011-11-29.
Copyright (c) 2011 Exa Networks. All rights reserved.
"""

import os
import sys

import traceback

from exaproxy.util.log import LogWriter

debug = os.environ.get('PDB',None)
#XXX
writer = LogWriter(True, 'print', None, port=None)

def bug_report (type, value, trace):
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
	print >> sys.stderr, writer.getHistory()
	print >> sys.stderr, ''
	print >> sys.stderr, ''
	print >> sys.stderr, '-- Traceback'
	print >> sys.stderr, ''
	print >> sys.stderr, ''
	traceback.print_exception(type,value,trace)
	print >> sys.stderr, ''
	print >> sys.stderr, ''
	print >> sys.stderr, '-'*80
	print >> sys.stderr, '-- Please provide the information above on :'
	print >> sys.stderr, '-- http://code.google.com/p/exaproxy/issues/entry'
	print >> sys.stderr, '-'*80
	print >> sys.stderr, ''
	print >> sys.stderr, ''

	#print >> sys.stderr, 'the program failed with message :', value

if debug is None:
	def intercept_nopdb (type, value, trace):
		bug_report(type, value, trace)
	sys.excepthook = intercept_nopdb
	log.pdb = False
elif debug not in ['0','']:
	def intercept_pdb (type, value, trace):
		bug_report(type, value, trace)
		import pdb
		pdb.pm()
	sys.excepthook = intercept_pdb
	log.pdb = True

del sys.argv[0]

if sys.argv:
	__file__ = os.path.abspath(sys.argv[0])
	__name__ = '__main__'
	execfile(sys.argv[0])
