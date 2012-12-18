# encoding: utf-8
'''
http.py

Created by Thomas Mangin on 2011-12-02.
Copyright (c) 2011 Exa Networks. All rights reserved.
'''

import sys
import time

from exaproxy.html.images import logo
from exaproxy.html.img import png

from exaproxy.configuration import load
version = load().proxy.version

_HTTP_NAMES = {
	'100': 'CONTINUE',
	'101': 'SWITCHING PROTOCOLS',
	'200': 'OK',
	'201': 'CREATED',
	'202': 'ACCEPTED',
	'203': 'NON-AUTHORITATIVE INFORMATION',
	'204': 'NO CONTENT',
	'205': 'RESET CONTENT',
	'206': 'PARTIAL CONTENT',
	'226': 'IM USED',
	'300': 'MULTIPLE CHOICES',
	'301': 'MOVED PERMANENTLY',
	'302': 'FOUND',
	'303': 'SEE OTHER',
	'304': 'NOT MODIFIED',
	'305': 'USE PROXY',
	'306': 'RESERVED',
	'307': 'TEMPORARY REDIRECT',
	'400': 'BAD REQUEST',
	'401': 'UNAUTHORIZED',
	'402': 'PAYMENT REQUIRED',
	'403': 'FORBIDDEN',
	'404': 'NOT FOUND',
	'405': 'METHOD NOT ALLOWED',
	'406': 'NOT ACCEPTABLE',
	'407': 'PROXY AUTHENTICATION REQUIRED',
	'408': 'REQUEST TIMEOUT',
	'409': 'CONFLICT',
	'410': 'GONE',
	'411': 'LENGTH REQUIRED',
	'412': 'PRECONDITION FAILED',
	'413': 'REQUEST ENTITY TOO LARGE',
	'414': 'REQUEST-URI TOO LONG',
	'415': 'UNSUPPORTED MEDIA TYPE',
	'416': 'REQUESTED RANGE NOT SATISFIABLE',
	'417': 'EXPECTATION FAILED',
	'500': 'INTERNAL SERVER ERROR',
	'501': 'NOT IMPLEMENTED',
	'502': 'BAD GATEWAY',
	'503': 'SERVICE UNAVAILABLE',
	'504': 'GATEWAY TIMEOUT',
	'505': 'HTTP VERSION NOT SUPPORTED',
}


def file_header(code, size, message):
	date = time.strftime('%c %Z')

	return '\r\n'.join([
		'HTTP/1.1 %s %s' % (str(code), _HTTP_NAMES.get(code,'-')),
		'Date: %s' % date,
		'Server: exaproxy/%s (%s)' % (str(version), str(sys.platform)),
		'Content-Length: %d' % size,
		'Connection: close',
		'Content-Type: text/html',
		'Cache-Control: no-store',
		'Pragma: no-cache',
		''
	])

def http (code,message):
	encoding = 'html' if '</html>' in message else 'plain'
	date = time.strftime('%c %Z')

	return '\r\n'.join([
		'HTTP/1.1 %s %s' % (str(code), _HTTP_NAMES.get(code,'-')),
		'Date: %s' % date,
		'Server: exaproxy/%s (%s)' % (str(version), str(sys.platform)),
		'Content-Length: %d' % len(message),
		'Content-Type: text/%s' % encoding,
		'Cache-Control: no-store',
		'Pragma: no-cache',
		'',
		message
	])

