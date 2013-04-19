#!/usr/bin/env python

import sys
import socket

pattern = ''.join(chr(_) for _ in range(0,256) if chr(_).isalpha())

for sizes in (
#	[str(_) for _ in range(1,10)],
	[str(1) for _ in range(0,0xffff)],
#	('ffff',),
#	('20000',),
):
	for te_key in ('Transfer-Encoding',):  # 'TE','Tranfer-Encoding'):  # everyone does a typo once in a while
		for te_value in ('chunked',):  # 'chunked, trailer','chunked,trailer','chunked, trailer, something;q=0.5', 'something;q=2, trailer, chunked,else;q=1.5'):
			s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			s.connect(("127.0.0.1", 3128))

			s.send(
				"POST /empty/ HTTTP/1.1\r\n"
				"Host: 127.0.0.1\r\n"
				"%s: %s\r\n"
				"Connection: close\r\n\r\n" % (te_key,te_value)
			)

			print "sending chunk sizes (%s: %s) :" % (te_key,te_value),
			for size in sizes:
				print size,
				sys.stdout.flush()
				length = int(size,16)
				repeat = length/len(pattern)+1
				chunk = (pattern * repeat)[:length]
				s.send("%s\r\n%s\r\n" % (size,chunk))
			print

			s.send("0\r\n\r\n")

			print s.recv(0x20000)

			s.close()
