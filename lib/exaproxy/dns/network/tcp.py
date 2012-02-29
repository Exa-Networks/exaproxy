# encoding: utf-8
"""
tcp.py

Created by David Farrar on 2012-02-08.
Copyright (c) 2011 Exa Networks. All rights reserved.
"""

import socket
from .ip import is_ipv4, is_ipv6

class TCPFactory:
	def create(self, dest_ip, port, timeout=2):
		if is_ipv4(dest_ip):
			sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
		elif is_ipv6(dest_ip):
			sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM, socket.IPPROTO_TCP)

		sock.bind((dest_ip, port))
		sock.settimeout(timeout)
		return sock

	def read(self, sock, buflen=1024):
		data = ''

		while True:
			buf = sock.recv(buflen)
			if not buf:
				break

			data += buf

		return data

	def close(self, sock):
		return sock.close()
