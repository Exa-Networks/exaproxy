#!/usr/bin/env python
# encoding: utf-8
"""
convert.py

Created by David Farrar on 2012-02-08.
Copyright (c) 2011 Exa Networks. All rights reserved.
"""

from struct import unpack
import socket
import array

def u8(s):
	return ord(s)

def u16(s):
	return unpack('>H', s)[0]

def u32(s):
	return unpack('>I', s)[0]

def dns_string(s):
	result = ''
	parts = []
	ptr = None
	remaining = len(s)

	while True:
		length = u8(s[0])
		remaining -= length + 1

		if length == 0:
			break

		if (length >> 6) == 3:
			ptr = u8(s[1])
			break

		if remaining <= 0:
			parts = []
			break

		parts.append(s[1:1+length])
		s = s[1+length:]

	return '.'.join(parts) if parts is not None else None, ptr




def dns_to_ipv4(ip, packet_s=''):
	return socket.inet_ntoa(ip)

def ipv4_to_dns(s, packet_s=''):
	return socket.inet_aton(ip)

def dns_to_ipv6(ip, packet_s=''):
	return socket.inet_ntop(socket.AF_INET6, ip)

def ipv6_to_dns(s, packet_s=''):
	return socket.inet_pton(socket.AF_INET6, s)

def dns_to_string(s, packet_s=''):
	value, ptr = dns_string(s)

	parts = [value] if value else []
	while ptr is not None:
		value, ptr = dns_string(packet_s[ptr:])

		if value:
			parts.append(value)

		elif value is None:
			parts = None
			break

	return '.'.join(parts) if parts is not None else None

def string_to_dns(s, packet_s=None):
	parts = (s.rstrip('.') + '.').split('.')
	return ''.join('%c%s' % (len(p), p) for p in parts)


