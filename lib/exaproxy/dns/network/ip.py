# encoding: utf-8
"""
ip.py

Created by David Farrar on 2012-02-08.
Copyright (c) 2011-2013  Exa Networks. All rights reserved.
"""

import socket

def is_ipv4(address):
	try:
		socket.inet_pton(socket.AF_INET, address)
		return True
	except socket.error:
		return False

def is_ipv6(address):
	try:
		socket.inet_pton(socket.AF_INET6, address)
		return True
	except socket.error:
		return False

def isip(address):
	return is_ipv4(address) or is_ipv6(address)
