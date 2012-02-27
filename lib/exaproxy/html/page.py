#!/usr/bin/env python
# encoding: utf-8
"""
page.py

Created by Thomas Mangin on 2012-02-08.
Copyright (c) 2012 Exa Networks. All rights reserved.
"""

import cgi

from .menu import Menu
from .graph import graph
from .mail import mail
from .img import png
from .index import index
from .licence import licence
from .humans import humans


options = [
	('/index.html',        'Home',),
	('/information.html',  'Information'),
	('/performance.html',  'Performance'),
	('/about.html',        'About'),
]

options_information = [
	('/information/introspection/supervisor.html',    'Introspection'),
	('/information/configuration.html', 'Configuration'),
	('/information/statistics.html',    'Statistics'),
]

options_performance = [
	('/performance/processes.html',   'Processes'),
	('/performance/connections.html', 'Connections'),
	('/performance/clients.html',     'Clients'),
	('/performance/servers.html',     'Servers'),
	('/performance/transfered.html',  'Transfered'),
	('/performance/loops.html',       'Loops'),
	('/performance/events.html',      'Events'),
]

options_about = [
	('/about/email.html',        'Email'),
	('/about/licence.html',      'Licence'),
]

menu = Menu(options,options_information,options_performance,options_about)


_listing = """\
<style type="text/css">
	.object { 
		width: 800px; margin-left: 20px; 
	}
	.object a {
		display: inline-block; width: 150px; text-align: left; font: 10pt Arial;
		padding: 5px 5px 5px 10px; text-decoration: none; color: #444;
		background: #eee; border: 1px solid #e4e4e4; margin: 1px 1px 1px 1px;
	}
	.object a:hover {
		color: #222; background: #e5e5e5; border: 1px solid #ccc;
	}
	.object	 .key {
		display: inline-block; width: 250px; text-align: left; font: 10pt Arial;
		padding: 5px 5px 5px 10px; text-decoration: none; color: #444;
		background: #eee; border: 1px solid #e4e4e4; margin: 1px 1px 1px 1px;
	}
	.object .value {
		display: inline-block; width: 500px; text-align: left; font: 10pt Arial;
		padding: 5px 5px 5px 5px; text-decoration: none; color: #111;
		background: #e5e5e5; border: 1px solid #ccc; margin: 1px 1px 1px 1px;
	}
</style>
<div class="object">
%s
</div>
"""""

class Page (object):

	def __init__(self,monitor):
		self.monitor = monitor
		self.email_sent = False

	def _introspection (self,objects):
		introduction = "<div style='padding: 10px 10px 10px 10px; font-weight:bold;'>Looking at the internal of ExaProxy for %s </div><br/>\n" % cgi.escape('.'.join(objects))
		link = cgi.escape('/'.join(objects[:-1])) if objects[:-1] else 'supervisor'
		line = ['<a href="/information/introspection/%s.html">Back to parent object</a><br/>' % link]
		for k,content in self.monitor.introspection(objects):
			link = '/information/introspection/%s.html' % cgi.escape('%s/%s' % ('/'.join(objects),k))
			line.append('<a href="%s">%s</a><span class="value">%s</span><br/>' % (link,k,cgi.escape(content)))
		return introduction + _listing % ('\n'.join(line))

	def _configuration (self):
		introduction = "<div style='padding: 10px 10px 10px 10px; font-weight:bold;'>ExaProxy Configuration</div><br/>\n"
		line = []
		for k,v in sorted(self.monitor.configuration().items()):
			line.append('<span class="key">%s</span><span class="value">&nbsp; %s</span><br/>' % (k,cgi.escape(v)))
		return introduction + _listing % ('\n'.join(line))

	def _statistics (self):
		introduction = "<div style='padding: 10px 10px 10px 10px; font-weight:bold;'>ExaProxy Statistics</div><br/>\n"
		line = []
		for k,v in sorted(self.monitor.statistics().items()):
			line.append('<span class="key">%s</span><span class="value">&nbsp; %s</span><br/>' % (k,cgi.escape(str(v))))
		return introduction + _listing % ('\n'.join(line))

	def _connections (self):
		return graph(
			self.monitor,
			'Proxy Connections',
			5000,
			[
				'running.proxy.clients.number',
				'running.proxy.download.opening',
				'running.proxy.download.established',
				'running.proxy.download',
				]
		)

	def _processes (self):
		return graph(
			self.monitor,
			'Proxy Processes',
			5000,
			[
				'running.processes.forked',
				'running.processes.min',
				'running.processes.max',
			]
		)

	def _sent (self):
		return graph(
			self.monitor,
			'Proxy Bytes Sent / seconds',
			5000,
			[
				'running.transfer.request',
			],
			True,
		)

	def _received (self):
		return graph(
			self.monitor,
			'Proxy Bytes Received / seconds',
			5000,
			[
				'running.transfer.download',
			],
			True,
		)

	def _transfer (self):
		return graph(
			self.monitor,
			'Proxy Bytes Transfered / seconds',
			5000,
			[
				'running.transfer.request',
				'running.transfer.download',
			],
			True,
		)

	def _loops (self):
		return graph(
			self.monitor,
			'Proxy Bytes Transfered / seconds',
			5000,
			[
				'running.load.loops',
			],
			True,
		)

	def _events (self):
		return graph(
			self.monitor,
			'Proxy Bytes Transfered / seconds',
			5000,
			[
				'running.load.events',
			],
			True,
		)

	def _email (self,args):
		if self.email_sent:
			return '<center><b>You can only send one email per time ExaProxy is started</b></center>'
		self.email_sent, message = mail.send(args)
		return message

	def html (self,path):
		if len(path) > 5000:
			return menu.root('<center><b>path is too long</b></center>')

		if path == '/':
			path = '/index.html'
			args = ''
		elif '?' in path:
			path,args = path.split('?',1)
		else:
			args = ''

		if not path.endswith('.html'):
			if path != '/humans.txt':
				return menu.root('<center><b>invalid extension</b></center>')
			return humans.txt
		if not path.startswith('/'):
			return menu.root('<center><b>invalid url</b></center>')

		sections = path[1:-5].split('/') + ['']
		if not sections[0]:
			return menu.root(index)
		section = sections[0]
		subsection = sections[1]

		if section == 'index':
			return menu.root(index)

		if section == 'information':
			if subsection == 'introspection':
				return menu.information(self._introspection(sections[2:-1]))
			if subsection == 'configuration':
				return menu.information(self._configuration())
			if subsection == 'statistics':
				return menu.information(self._statistics())
			return menu.information(index)

		if section == 'performance':
			if subsection == 'processes':
				return menu.performance(self._processes())
			if subsection == 'connections':
				return menu.performance(self._connections())
			if subsection == 'servers':
				return menu.performance(self._sent())
			if subsection == 'clients':
				return menu.performance(self._received())
			if subsection == 'transfered':
				return menu.performance(self._transfer())
			if subsection == 'loops':
				return menu.performance(self._loops())
			if subsection == 'events':
				return menu.performance(self._events())
			return menu.performance(index)

		if section == 'about':
			if subsection == 'email':
				if args:
					return menu.about(self._email(args))
				return menu.about(mail.form)
			if subsection == 'licence':
				return menu.about(licence)
			return menu.about('')

		if section == 'humans':
			return menu.root(humans.html)
		return menu.root('')
