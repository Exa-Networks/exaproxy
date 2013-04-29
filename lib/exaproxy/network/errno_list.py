# encoding: utf-8
"""
server.py

Created by Thomas Mangin on 2011-11-30.
Copyright (c) 2011-2013  Exa Networks. All rights reserved.
"""

# http://code.google.com/speed/articles/web-metrics.html

import errno

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
	errno.ECONNRESET, errno.ETIMEDOUT,
	errno.EINVAL,
))

errno_unavailable = set((
	errno.ECONNREFUSED, errno.EHOSTUNREACH,
))
