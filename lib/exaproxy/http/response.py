#!/usr/bin/env python
# encoding: utf-8
"""
http.py

Created by Thomas Mangin on 2011-12-02.
Copyright (c) 2011 Exa Networks. All rights reserved.
"""

import sys
import time

from exaproxy.configuration import load
from exaproxy.util.version import version
from .images import logo

def file_header(code, size, message):
	date = time.strftime('%c %Z')

	return """HTTP/1.1 %s OK
Date: %s
Server: exaproxy/%s (%s)
Content-Length: %d
Connection: close
Content-Type: text/html
Cache-control: private
Pragma: no-cache

""" % (str(code), date, str(version), str(sys.platform), size)




def http (code,message):
	encoding = 'html' if '</html>' in message else 'plain'
	return """\
HTTP/1.1 %s OK
Date: Fri, 02 Dec 2011 09:29:44 GMT
Server: exaproxy/%s (%s)
Content-Length: %d
Content-Type: text/%s
Cache-control: private
Pragma: no-cache

%s""" % (str(code),str(version),sys.platform,len(message),encoding,message)

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


