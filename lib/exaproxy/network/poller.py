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

import select
from exaproxy.util.logger import logger


#if hasattr(select, 'epoll'):
#	poll = select.epoll
#if hasattr(select, 'poll'):
#	poll = select.poll
if hasattr(select, 'select'):
	poll = select.select
else:
	raise ImportError, 'what kind of select module is this'


errno_block = set((
	errno.EINPROGRESS, errno.EALREADY,
	errno.EAGAIN, errno.EWOULDBLOCK,
	errno.EINTR, errno.EDEADLK,
	errno.ENOMEM,
))

errno_fatal = set((
	errno.ECONNABORTED, errno.EPIPE,
	errno.ECONNREFUSED, errno.EBADF,
	errno.ESHUTDOWN, errno.ENOTCONN,
	errno.ECONNRESET, 
))


def poll_select(read, write, timeout=None):
	try:
		r, w, x = poll(read, write, read + write, timeout)
	except socket.error, e:
		if e.args[0] in errno_block:
			logger.error('select', 'select not ready, errno %d: %s' % (e.args[0], errno.errorcode.get(e.args[0], '')))
			return [], [], []

		if e.args[0] in errno_fatal:
			logger.error('select', 'select problem, errno %d: %s' % (e.args[0], errno.errorcode.get(e.args[0], '')))
			logger.error('select', 'poller read  : %s' % str(read))
			logger.error('select', 'poller write : %s' % str(write))
			logger.error('select', 'read : %s' % str(read))
		else:
			logger.error('select', 'select problem, debug it. errno %d: %s' % (e.args[0], errno.errorcode.get(e.args[0], '')))

		for f in read:
			try:
				poll([f], [], [f], 0.1)
			except socket.error:
				print "CANNOT POLL (read): %s" % str(f)
				logger.error('select', 'can not poll (read) : %s' % str(f))

		for f in write:
			try:
				poll([], [f], [f], 0.1)
			except socket.error:
				print "CANNOT POLL (write): %s" % str(f)
				logger.error('select', 'can not poll (write) : %s' % str(f))

		raise e
	except (ValueError, AttributeError, TypeError), e:
		logger.error('select',"fatal error encountered during select - %s %s" % (type(e),str(e)))
		raise e
	except select.error, e:
		if e.args[0] in errno_block:
			return [], [], []
		logger.error('select',"fatal error encountered during select - %s %s" % (type(e),str(e)))
		raise e
	except Exception, e:
		logger.error('select',"fatal error encountered during select - %s %s" % (type(e),str(e)))
		raise e
			
	return r, w, x
