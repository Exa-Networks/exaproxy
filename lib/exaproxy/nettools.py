#!/usr/bin/env python
# encoding: utf-8
"""
nettools.py

Created by Thomas Mangin on 2011-11-30.
Copyright (c) 2011 Exa Networks. All rights reserved.
"""

import socket
import errno

from .util.logger import logger



def is_ipv4(addr):
	try:
		socket.inet_pton(socket.AF_INET, addr)
	except socket.error:
		return False

	return True

def is_ipv6(addr):
	try:
		socket.inet_pton(socket.AF_INET6, addr)
	except socket.error:
		return False

	return True

	
def bound_tcp_socket(ip, port):
	if is_ipv6(ip):
		sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM, socket.IPPROTO_TCP)
	elif is_ipv4(ip):
		sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
	else:
		sock = None

	if sock is not None:
		try:
			sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
			sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
		except AttributeError:
			pass

		try:
			sock.bind((ip, port))
		except socket.error, e:
			if e.errno == errno.EADDRINUSE:
				logger.error('server', 'could not listen, port already in use %s:%d' % (ip, port))
			elif e.errno == errno.EADDRNOAVAIL:
				logger.error('server', 'could not listen, invalid address %s:%d' % (ip, port))
			else:
				logger.error('server','could not listen on %s:%d - %s' % (ip,port,str(e)))

			sock = None

	return sock

def connected_tcp_socket(ip, port):
	if is_ipv6(ip):
		sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM, socket.IPPROTO_TCP)
	elif is_ipv4(ip):
		sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
	else:
		print "BAD IP - SOCKET IS NONE"
		sock = None

	if sock is not None:
		try:
			sock.connect((ip, port))
		except socket.error, e:
			print "ERROR - SOCKET IS NONE", type(e), e
			sock = None

	return sock
