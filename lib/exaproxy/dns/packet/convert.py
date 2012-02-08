#!/usr/bin/env python
# encoding: utf-8
"""
convert.py

Created by David Farrar on 2012-02-08.
Copyright (c) 2011 Exa Networks. All rights reserved.
"""

from struct import unpack
import socket

def u8(s):
	return ord(s)

def u16(s):
	return unpack('>H', s)[0]

def u32(s):
	return unpack('>I', s)[0]

def ipv4_ntoa(ip):
	return socket.inet_ntoa(ip)

def ipv4_aton(s):
	return socket.inet_aton(ip)
