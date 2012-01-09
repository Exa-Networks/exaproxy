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
from .util.logger import logger


#if hasattr(select, 'epoll'):
#	poll = select.epoll
#if hasattr(select, 'poll'):
#	poll = select.poll
if hasattr(select, 'select'):
	poll = select.select
else:
	raise ImportError, 'what kind of select module is this'


_block_errors = (errno.EAGAIN, errno.EWOULDBLOCK, errno.EINTR,)
_fatal_errors = (errno.EINVAL,errno.EBADF,) # (please do not change this list)



class SelectError (Exception):
	pass


def poller_select(read, write, timeout=None):
	try:
		r, w, x = poll(read, write, read + write, timeout)

	except socket.error, e:
		if e.errno in _block_errs:
			logger.error('server', 'select not ready, errno %d: %s' % (e.errno, errno.errorcode.get(e.errno, '')))
			r, w, x = [], [], []

		elif e.errno in _fatal_errors:
			logger.error('server', 'select problem, errno %d: %s' % (e.errno, errno.errorcode.get(e.errno, '')))

		else:
			logger.error('server', 'select problem, debug it. errno %d: %s' % (e.errno, errno.errorcode.get(e.errno, '')))
			raise SelectError, str(e)
	except (ValueError, AttributeError, TypeError), e:
		logger.error('server',"fatal error encountered during select - %s %s" % (type(e),str(e)))
		raise SelectError, str(e)
	except Exception, e:
		logger.error('server',"fatal error encountered during select - %s %s" % (type(e),str(e)))
		raise SelectError, str(e)
			
	return r, w, x
