#!/usr/bin/env python
# encoding: utf-8
"""
http.py

Created by Thomas Mangin on 2011-12-02.
Copyright (c) 2011 Exa Networks. All rights reserved.
"""

import sys
import time

from exaproxy.util.version import version
from .images import logo


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

	return """HTTP/1.1 %s %s
Date: %s
Server: exaproxy/%s (%s)
Content-Length: %d
Connection: close
Content-Type: text/html
Cache-control: private
Pragma: no-cache

""" % (str(code), _HTTP_NAMES.get(code,'-'),date, str(version), str(sys.platform), size)




def http (code,message):
	encoding = 'html' if '</html>' in message else 'plain'
	date = time.strftime('%c %Z')
	return """\
HTTP/1.1 %s %s
Date: %s
Server: exaproxy/%s (%s)
Content-Length: %d
Content-Type: text/%s
Cache-control: private
Pragma: no-cache

%s""" % (str(code),_HTTP_NAMES.get(code,'-'),date,str(version),sys.platform,len(message),encoding,message)

def png (base64):
	return '<img src="data:image/png;base64,%s"/>' % base64

def jpg (base64):
	return '<img src="data:image/jpeg;base64,%s"/>' % base64

def html (title,header,color='#FF0000',image=png(logo),menu='',text='',):
	if header: header += '<br/>'
	return """\
<html>
	<head>
		<title>%s</title>
		<meta http-equiv="cache-control" content="no-cache">
	</head>
	<body leftmargin="0" topmargin="0" rightmargin="0" bgcolor="#FFFFFF" text="#000000" link="#0000FF" alink="#0000FF" vlink="#0000FF">
		<center>
			<div style="padding:15; color: #FFFFFF; background: %s; font-size: 40px; font-family: verdana,sans-serif,arial; font-weight: bold; border-bottom: solid 1px #A0A0A0;">
				%s
				%s
			</div>
		</center>
		<br/>
		%s
		<br/>
		<br/>
		%s
		<br/>
		<br/>
	</body>
</html>

""" % (title,color,header,image,menu,text)


