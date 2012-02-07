#!/usr/bin/env python
# encoding: utf-8
"""
monitor.py

Created by Thomas Mangin on 2012-02-05.
Copyright (c) 2012 Exa Networks. All rights reserved.
"""

import cgi
import pprint
from .response import html, menu

class Monitor (object):
	
	options = {
		1 : ('/index.html' , 'Home'),
		2 : ('/objects/supervisor.html' , 'Instrospection'),
		3 : ('/stats/index.html' , 'Statistics'),
	}

	_title = 'ExaProxy'
	_menu = menu(options)
	_html = html(_title,_title,'#00BB55',_menu,'*string*').replace('%','%%').replace('*string*','%s')

	_index = """\
	<center>
		<b>Welcome to ExaProxy Management web server.</b>
		<br/>
		<br/>
		Those pages are under development (this sentence brings me back to the 90's) :D.<br/>
		We intend to add here real time information about the Proxy and other nice things.<br>
	</center>
	"""

	def __init__(self,supervisor):
		self.supervisor = supervisor

	def _page (self,message):
		return self._html % message

	def html_object (self,prefix,obj):
		ks = [_ for _ in dir(obj) ] #if not _.startswith('__')]
		line = []

		for k in ks:
			if k.startswith('__') and k.endswith('__'):
				continue
			content = cgi.escape(str(getattr(obj,k)))
			link = '%s.%s' % (prefix,k)
			line.append('<li/> <a href="/objects/%s.html">%s</a> : %s' % (link,k,pprint.pformat(content)))

		return """
<div style='padding-left:10px;'>objects of <b>%s</b> are :
	<ul>
%s
	</ul>
</div>
""" % (prefix,'\n'.join(line))


	def html (self,path):
		if len(path) > 200:
			return self._page('<center><b>path is too long</b></center>')
		
		if path in ('/','/index.html'):
			return self._page(self._index)

		elif path.startswith('/objects/'):
			path = path[9:]
			if not path.startswith('supervisor.'):
				return self._page(self.html_index())

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
						return self._page('<center><b>so such object</b></center>')
					obj = getattr(obj,key)
					prefix = "%s.%s" % (prefix,key)
			else:
				prefix = 'supervisor'

			return self._page(self.html_object(prefix,obj))
		else:
			return self._page('<center><b>are you looking for an easter egg ?</b></center>')
