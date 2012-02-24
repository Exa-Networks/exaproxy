#!/usr/bin/env python
# encoding: utf-8
"""
nettools.py

Created by Thomas Mangin on 2011-11-30.
Copyright (c) 2011 Exa Networks. All rights reserved.
"""

import socket
import errno

from exaproxy.util.logger import logger
from exaproxy.network.errno_list import errno_block


def _ipv4(address):
	try:
		socket.inet_pton(socket.AF_INET, address)
		return True
	except socket.error:
		return False

def _ipv6(address):
	try:
		socket.inet_pton(socket.AF_INET6, address)
		return True
	except socket.error:
		return False

def isip(address):
	return _ipv4(address) or _ipv6(address)

def listen (ip,port,timeout=None,backlog=0):
	try:
		if _ipv6(ip):
			s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM, socket.IPPROTO_TCP)
			try:
				s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
				s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
			except AttributeError:
				pass
			s.bind((ip,port,0,0))
		elif _ipv4(ip):
			s = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
			try:
				s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
				s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
			except AttributeError:
				pass
			s.bind((ip,port))
		else:
			return None
		if timeout:
			s.settimeout(timeout)
		##s.setblocking(0)
		s.listen(backlog)
		return s
	except socket.error, e:
		if e.args[0] == errno.EADDRINUSE:
			logger.debug('server','could not listen, port already in use %s:%d' % (ip,port))
		elif e.args[0] == errno.EADDRNOTAVAIL:
			logger.debug('server','could not listen, invalid address %s:%d' % (ip,port))
		else:
			logger.debug('server','could not listen on %s:%d - %s' % (ip,port,str(e)))
		return None


def connect (ip,port,immediate=True):
	try:
		if _ipv6(ip):
			s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM, socket.IPPROTO_TCP)
		elif _ipv4(ip):
			s = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
		else:
			return None
	except socket.error,e:
		return None

#	try:
#		s.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 64*1024)
#	except socket.error, e:
#		print "CANNOT SET RCVBUF"
#		logger.debug('server','could not set sock rcvbuf size')
#	except Exception,e:
#		print "*"*10
#		print type(e),str(e)
#		raise

	if immediate:
		try:
			# diable Nagle's algorithm (no grouping of packets)
			s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
		except AttributeError:
			pass

	try:
		s.setblocking(0)
		s.connect((ip, port))
	except socket.error,e:
		if e.args[0] == errno.EINPROGRESS:
			pass

		elif e.args[0] in errno_block:
			pass

		else:
			s = None

	return s
