#!/usr/bin/env python

import sys
import socket

pattern = ''.join(chr(_) for _ in range(0,256) if chr(_).isalpha())

for sizes in (
	[str(_) for _ in range(1,10)],
	[str(1) for _ in range(0,0xff)],
	['ffff',],
	['20000',],
	(),
):
	for te_key in ('Transfer-Encoding', 'TE'):
		for te_value in ('chunked', 'chunked, trailer','chunked,trailer','trailers, deflate;q=0.5', 'something;q=1.5, trailer, chunked,else;q=0.5', 'chunked, something;q=1.5'):
			s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			s.connect(('127.0.0.1', 3128))

			request = \
				'POST /empty/ HTTTP/1.1\r\n' \
				'Host: 127.0.0.1\r\n' \
				'%s' \
				'Connection: close\r\n\r\n' % ('%s: %s\r\n' % (te_key,te_value) if te_value else '')

			s.send(request)

			debug = ['\n']
			debug.append('=' * 80)
			debug.append('sending chunk sizes (%s: %s) :' % (te_key,te_value))
			debug.append('%s' % ' '.join(sizes))
			debug.append('\n')

			if 'chunk' in request and not ';q=1.5' in request:
				sys.stdout.write('%-8s chunk size %-6d %-65s' % ('single' if len(sizes) == 1 else 'multiple', sum(int(_,16) for _ in sizes),'-' if not te_key else '%s: %s' % (te_key,te_value)))

				for size in sizes:
					sys.stdout.flush()
					length = int(size,16)
					repeat = length/len(pattern)+1
					chunk = (pattern * repeat)[:length]
					sent = '%s\r\n%s\r\n' % (size,chunk)
					s.send(sent)
					request += sent.replace('\t', '\\t').replace('\r', '\\r').replace('\n', '\\n\n')

				request += '0\\r\\n\\r\\n\n'
				s.send('0\r\n\r\n')
			else:
				sys.stdout.write('no chunk                   %-65s' % ('-' if not te_key else '%s: %s' % (te_key,te_value)))


			debug.append('[[%s]]' % request.replace('\t', '\\t').replace('\r', '\\r').replace('\n', '\\n\n'))
			debug.append('\n')

			try:
				data = s.recv(0x20000)
			except KeyboardInterrupt:
				print '\n'.join(debug)
				sys.exit(1)
			s.close()

			if '200' in data:
				sys.stdout.write('page received\n')
				sys.stdout.flush()
			elif '501 Method Not Implemented' in data:
				sys.stdout.write('not implemented\n')
				sys.stdout.flush()
			else:
				debug.append('[[%s]]' % data.replace('\t', '\\t').replace('\r', '\\r').replace('\n', '\\n\n'))
				print '\n'.join(debug)
				sys.stdout.flush()
				sys.exit(1)
