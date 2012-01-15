#!/usr/bin/env python
# encoding: utf-8
"""
server.py

Created by Thomas Mangin on 2011-11-30.
Copyright (c) 2011 Exa Networks. All rights reserved.
"""

# http://code.google.com/speed/articles/web-metrics.html

import os
import struct
import time
import socket
import errno

import select as select
from exaproxy.util.logger import logger


#if hasattr(select, 'epoll'):
#	poll = select.epoll
#if hasattr(select, 'poll'):
#	poll = select.poll
if hasattr(select, 'select'):
	poll = select.select
else:
	raise ImportError, 'what kind of select module is this'


#	_blocking_errs = set(
#		errno.EAGAIN, errno.EWOULDBLOCK, 
#		errno.EINTR, errno.ETIMEDOUT,
#	)

_block_errors = set((
	errno.EAGAIN, errno.EWOULDBLOCK,
	errno.EINTR,
))

#	_fatal_errs = set(
#		errno.ECONNABORTED, errno.EPIPE,
#		errno.ECONNREFUSED, errno.EBADF,
#		errno.ESHUTDOWN, errno.ENOTCONN,
#		errno.ECONNRESET, 
#	)

_fatal_errors = set((
	errno.EINVAL,
	errno.EBADF,
)) # (please do not change this list) # XXX: Thomas asks why : it is only used in this file .. and it seems the list is short


class SelectError (Exception):
	pass


def select(read, write, timeout=None):
	try:
		r, w, x = poll(read, write, read + write, timeout)

	except socket.error, e:
		if e.errno in _block_errors:
			logger.error('select', 'select not ready, errno %d: %s' % (e.errno, errno.errorcode.get(e.errno, '')))
			return [], [], []

		if e.errno in _fatal_errors:
			logger.error('select', 'select problem, errno %d: %s' % (e.errno, errno.errorcode.get(e.errno, '')))
			logger.error('select', 'poller read  : %s' % str(read))
			logger.error('select', 'poller write : %s' % str(write))
			logger.error('select', 'read : %s' % str(read))
		else:
			logger.error('select', 'select problem, debug it. errno %d: %s' % (e.errno, errno.errorcode.get(e.errno, '')))

		for f in read:
			try:
				poll([f], [], [f], 0.1)
			except socket.errno:
				logger.error('select', 'can not poll (read) : %s' % str(f))

		for f in write:
			try:
				poll([], [f], [f], 0.1)
			except socket.errno:
				logger.error('select', 'can not poll (write) : %s' % str(f))

		raise SelectError, str(e)
	except (ValueError, AttributeError, TypeError), e:
		logger.error('select',"fatal error encountered during select - %s %s" % (type(e),str(e)))
		raise SelectError, str(e)
	except Exception, e:
		logger.error('select',"fatal error encountered during select - %s %s" % (type(e),str(e)))
		raise SelectError, str(e)
			
	return r, w, x
