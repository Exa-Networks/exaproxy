# encoding: utf-8
"""
nettools.py

Created by Thomas Mangin on 2011-11-30.
Copyright (c) 2011-2013  Exa Networks. All rights reserved.
"""

import socket
import errno

from exaproxy.util.log.logger import Logger
from exaproxy.network.errno_list import errno_block
from exaproxy.configuration import load

configuration = load()
log = Logger('server', configuration.log.server)

def isipv4(address):
	try:
		socket.inet_pton(socket.AF_INET, address)
		return True
	except socket.error:
		return False

def isipv6(address):
	try:
		socket.inet_pton(socket.AF_INET6, address)
		return True
	except socket.error:
		return False

def isip(address):
	return isipv4(address) or isipv6(address)

def listen (ip,port,timeout=None,backlog=0):
	try:
		if isipv6(ip):
			s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM, socket.IPPROTO_TCP)
			try:
				s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
				s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
			except (AttributeError, socket.error):
				pass
			s.bind((ip,port,0,0))
		elif isipv4(ip):
			s = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
			try:
				s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
				s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
			except (AttributeError, socket.error):
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
			log.debug('could not listen, port already in use %s:%d' % (ip,port))
		elif e.args[0] == errno.EADDRNOTAVAIL:
			log.debug('could not listen, invalid address %s:%d' % (ip,port))
		else:
			log.debug('could not listen on %s:%d - %s' % (ip,port,str(e)))
		return None


def connect (ip,port,bind,immediate=True):
	try:
		if isipv6(ip):
			s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM, socket.IPPROTO_TCP)
		elif isipv4(ip):
			s = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
		else:
			return None
	except socket.error,e:
		return None

#	try:
#		s.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 64*1024)
#	except socket.error, e:
#		print "CANNOT SET RCVBUF"
#		log.debug('server','could not set sock rcvbuf size')
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

	if bind not in ('0.0.0.0','::'):
		try:
			s.bind((bind,0))
		except socket.error,e:
			log.critical('could not bind to the requested ip "%s" - using OS default' % bind)

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
