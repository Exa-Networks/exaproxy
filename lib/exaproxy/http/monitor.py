#!/usr/bin/env python
# encoding: utf-8
"""
monitor.py

Created by Thomas Mangin on 2012-02-05.
Copyright (c) 2012 Exa Networks. All rights reserved.
"""

import cgi
import pprint
from .response import image

class Monitor (object):
	options = {
		'/index.html'   : 'This page',
		'/objects/supervisor.html' : 'live instrospection',
	}

	def __init__(self,supervisor):
		self.supervisor = supervisor

	def _format (self,message):
		title = 'ExaProxy monitoring webpage'
		return """\
<html>
	<head>
		<title>%s</title>
		<meta http-equiv="cache-control" content="no-cache">
	</head>
	<body leftmargin="0" topmargin="0" rightmargin="0" bgcolor="#FFFFFF" text="#000000" link="#0000FF" alink="#0000FF" vlink="#0000FF">
		<center>
			<div style="padding:15; color: #FFFFFF; background: #00BB55; font-size: 40px; font-family: verdana,sans-serif,arial; font-weight: bold; border-bottom: solid 1px #A0A0A0;">
				%s
				<br>
				<img src="data:image/png;base64,%s"/>
			</div>
		</center>
		<br/>
		%s
	</body>
</html>
""" % (title,title,image,message)

	def html_index (self):
		return """valid commands are :\n<ul>\n%s\n</ul>""" % '\n'.join(['<li/> <a href="%s">%s</a>' % _ for _ in zip(self.options.keys(),self.options.values())])

	def html_object (self,prefix,obj):
		ks = [_ for _ in dir(obj) ] #if not _.startswith('__')]
		line = []

		for k in ks:
			content = cgi.escape(str(getattr(obj,k)))
			link = '%s.%s' % (prefix,k)
			line.append('<li/> <a href="/objects/%s.html">%s</a> : %s' % (link,k,pprint.pformat(content)))

		return """<div style='padding-left:10px;'>objects of <b>%s</b> are :\n<ul>\n%s\n</ul></div>""" % (prefix,'\n'.join(line))


	def html (self,path):
		if len(path) > 200:
			return self._format('<center><b>path is too long</b></center>')
		
		if path in ('/','/index.html'):
			return self._format(self.html_index())

		elif path.startswith('/objects/'):
			path = path[9:]
			if not path.startswith('supervisor.'):
				return self._format(self.html_index())

			if path and path.endswith('.html'):
				prefix = path[:-5]
			prefix = prefix[11:]
			obj = self.supervisor

			if prefix:
				parts = prefix.split('.')
				prefix = 'supervisor'
				for key in parts:
					ks = [_ for _ in dir(obj) if not _.startswith('__')]
					if not key in ks:
						return self._format('<center><b>so such object</b></center>')
					obj = getattr(obj,key)
					prefix = "%s.%s" % (prefix,key)
			else:
				prefix = 'supervisor'

			return self._format(self.html_object(prefix,obj))
		else:
			return self._format('<center><b>unknow command</b></center>')
