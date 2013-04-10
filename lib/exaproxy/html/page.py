# encoding: utf-8
"""
page.py

Created by Thomas Mangin on 2012-02-08.
Copyright (c) 2011-2013 Exa Networks. All rights reserved.
"""

import cgi
import json

from .menu import Menu
from .graph import graph
from .mail import mail
from .index import index
from .licence import licence
from .humans import humans


options = (
	('/index.html', 'Home', (
	)),
	('/information.html', 'Information', (
		('/information/introspection/supervisor.html', 'Introspection'),
		('/information/configuration.html', 'Configuration'),
		('/information/statistics.html', 'Statistics'),
	)),
	('/performance.html', 'Performance', (
		('/performance/processes.html', 'Processes'),
		('/performance/connections.html', 'Connections'),
		('/performance/clients.html', 'Clients'),
		('/performance/servers.html', 'Servers'),
		('/performance/transfered.html', 'Transfered'),
		('/performance/loops.html', 'Loops'),
		('/performance/events.html', 'Events'),
		('/performance/queue.html', 'Queue'),
	)),
	('/update.html', 'Update', (
	)),
	('/about.html', 'About', (
		('/about/email.html', 'Email'),
		('/about/licence.html', 'Licence'),
	)),
)

menu = Menu(options)


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

	def __init__(self,supervisor):
		self.supervisor = supervisor
		self.monitor = supervisor.monitor
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
			line.append('<span class="key">%s</span><span class="value">&nbsp; %s</span><br/>' % (k,cgi.escape(str(v))))
		return introduction + _listing % ('\n'.join(line))

	def _statistics (self):
		introduction = "<div style='padding: 10px 10px 10px 10px; font-weight:bold;'>ExaProxy Statistics</div><br/>\n"
		line = []
		for k,v in sorted(self.monitor.statistics().items()):
			line.append('<span class="key">%s</span><span class="value">&nbsp; %s</span><br/>' % (k,cgi.escape(str(str(v)))))
		return introduction + _listing % ('\n'.join(line))

	def _connections (self):
		return graph(
			self.monitor,
			'Proxy Connections',
			20000,
			[
				'running.proxy.clients.number',
				'running.proxy.download.opening',
				'running.proxy.download.established',
				'running.proxy.download.clients',
				]
		)

	def _processes (self):
		return graph(
			self.monitor,
			'Proxy Processes',
			20000,
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
			20000,
			[
				'running.transfer.request',
			],
			True,
		)

	def _received (self):
		return graph(
			self.monitor,
			'Proxy Bytes Received / seconds',
			20000,
			[
				'running.transfer.download',
			],
			True,
		)

	def _transfer (self):
		return graph(
			self.monitor,
			'Proxy Bytes Transfered / seconds',
			20000,
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
			20000,
			[
				'running.load.loops',
			],
			True,
		)

	def _events (self):
		return graph(
			self.monitor,
			'Proxy Bytes Transfered / seconds',
			20000,
			[
				'running.load.events',
			],
			True,
		)

	def _queue (self):
		return graph(
			self.monitor,
			'Proxy Bytes Sent / seconds',
			20000,
			[
				'running.queue.size',
			],
			True,
		)

	def _update (self):
		form = '<form action="/update/commit" method="get">%s: <input type="text" name="%s" value="%s"><input type="submit" value="Submit"></form>'

		change = {
			'exaproxy.redirector.minimum' : self.supervisor.manager.low,
			'exaproxy.redirector.maximum' : self.supervisor.manager.high,
		}

		forms = []
		for name in ('exaproxy.redirector.minimum', 'exaproxy.redirector.maximum'):
			value = change[name]
			forms.append(form % (name,name,value))
		return '<pre style="margin-left:40px;">\n' + '\n'.join(forms)

	def _email (self,args):
		if self.email_sent:
			return '<center><b>You can only send one email per time ExaProxy is started</b></center>'
		self.email_sent, message = mail.send(args)
		return message

	def _json_running (self):
		return json.dumps(self.monitor.history[-1],sort_keys=True,indent=2,separators=(',', ': '))

	def _json_configuration (self):
		return json.dumps(self.monitor.configuration(),sort_keys=True,indent=2,separators=(',', ': '))

	def html (self,path):
		if len(path) > 5000:
			return menu('<center><b>path is too long</b></center>')

		if path == '/':
			path = '/index.html'
			args = ''
		elif '?' in path:
			path,args = path.split('?',1)
		else:
			args = ''

		if not path.startswith('/'):
			return menu('<center><b>invalid url</b></center>')
		elif not path.endswith('.html'):
			if path == '/humans.txt':
				return humans.txt
			if path not in ('/json','/json/running','/json/configuration','/update/commit'):
				return menu('<center><b>invalid url</b></center>')
			sections = path[1:].split('/',1) + ['']
		else:
			sections = path[1:-5].split('/',1) + ['']

		if not sections[0]:
			return menu(index)
		section = sections[0]
		subsection = sections[1]

		if section == 'json':
			if subsection == 'running':
				return self._json_running()
			if subsection == 'configuration':
				return self._json_configuration()
			return '{ "errror" : "invalid url", "valid-paths": [ "/json/running", "/json/configuration" ] }'

		if section == 'index':
			return menu(index)

		if section == 'information':
			if subsection == 'introspection':
				return menu(self._introspection(sections[2:-1]))
			if subsection == 'configuration':
				return menu(self._configuration())
			if subsection == 'statistics':
				return menu(self._statistics())
			return menu(index)

		if section == 'performance':
			if subsection == 'processes':
				return menu(self._processes())
			if subsection == 'connections':
				return menu(self._connections())
			if subsection == 'servers':
				return menu(self._sent())
			if subsection == 'clients':
				return menu(self._received())
			if subsection == 'transfered':
				return menu(self._transfer())
			if subsection == 'loops':
				return menu(self._loops())
			if subsection == 'events':
				return menu(self._events())
			if subsection == 'queue':
				return menu(self._queue())
			return menu(index)

		if section == 'update':
			if subsection == 'commit':
				if '=' in args:
					key,value = args.split('=',1)

					if key == 'exaproxy.redirector.minimum':
						if value.isdigit():  # this prevents negative values
							setting = int(value)
							if setting > self.supervisor.manager.high:
								return menu(self._update() + '<div style="color: red; padding-top: 3em;">value is higher than exaproxy.redirector.maximum</div>')
							self.supervisor.manager.low = setting
							return menu(self._update() + '<div style="color: green; padding-top: 3em;">changed successfully</div>')

					if key == 'exaproxy.redirector.maximum':
						if value.isdigit():
							setting = int(value)
							if setting < self.supervisor.manager.low:
								return menu(self._update() + '<div style="color: red; padding-top: 3em;">value is lower than exaproxy.redirector.minimum</div>')
							self.supervisor.manager.high = setting
							return menu(self._update() + '<div style="color: green; padding-top: 3em;">changed successfully</div>')

					return menu(self._update() + '<div style="color: red; padding-top: 3em;">invalid request</div>')

			return menu(self._update())

		if section == 'about':
			if subsection == 'email':
				if args:
					return menu(self._email(args))
				return menu(mail.form)
			if subsection == 'licence':
				return menu(licence)
			return menu('')

		if section == 'humans':
			return menu(humans.html)
		return menu('')
