# encoding: utf-8
"""
page.py

Created by Thomas Mangin on 2012-02-08.
Copyright (c) 2011-2013 Exa Networks. All rights reserved.
"""

import cgi
import json

from urllib import unquote

from .menu import Menu
from .graph import graph
from .mail import mail
from .index import index
from .licence import licence
from .humans import humans

from exaproxy.util.log.history import History
from exaproxy.util.log.logger import Logger

options = (
	('Information', '/information.html', (
		('Introspection', '/information/introspection/supervisor.html', False),
		('Configuration', '/information/configuration.html', False),
		('Statistics', '/information/statistics.html', False),
		('Logs', '/information/logs.html', True),
	)),
	('Performance', '/performance.html', (
		('Loops', '/performance/loops.html', False),
		('Events', '/performance/events.html', False),
		('Processes', '/performance/processes.html', False),
		('Queue', '/performance/queue.html', False),
		('Connections', '/performance/connections.html', False),
		('Transfered', '/performance/transfered.html', False),
		('Clients', '/performance/clients.html', False),
		('Servers', '/performance/servers.html', False),
	)),
	('Control', '/control.html', (
		('Workers', '/control/workers.html', False),
		('Debug', '/control/debug.html', False),
	)),
	('JSON', '/index.html', (
		('running', '/json/running', True),
		('configuration', '/json/configuration', True),
	)),

	('About', '/about.html', (
		('Email', '/about/email.html', False),
		('Licence', '/about/licence.html', False),
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

def Bpstobps (bytes):
	return bytes * 8

class Page (object):

	def __init__(self,supervisor):
		self.supervisor = supervisor
		self.monitor = supervisor.monitor
		self.email_sent = False
		self.log = Logger('web', supervisor.configuration.log.web)

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
			'Connections',
			20000,
			[
				'clients.established',
				'servers.opening',
				'servers.established',
				]
		)

	def _processes (self):
		return graph(
			self.monitor,
			'Forked processes',
			20000,
			[
				'processes.forked',
				'processes.min',
				'processes.max',
			]
		)

	def _clients (self):
		return graph(
			self.monitor,
			'Bits/seconds received from clients',
			20000,
			[
				'transfer.client4',
				'transfer.client6',
			],
			True,
			adaptor=Bpstobps,
		)

	def _servers (self):
		return graph(
			self.monitor,
			'Bits/seconds received from servers',
			20000,
			[
				'transfer.content4',
				'transfer.content6',
			],
			True,
			adaptor=Bpstobps,
		)

	def _transfer (self):
		return graph(
			self.monitor,
			'Bits/seconds received',
			20000,
			[
				'transfer.client',
				'transfer.content',
			],
			True,
			adaptor=Bpstobps,
		)

	def _loops (self):
		return graph(
			self.monitor,
			'Reactor loops',
			20000,
			[
				'load.loops',
			],
			True,
		)

	def _events (self):
		return graph(
			self.monitor,
			'Sockets which became readeable',
			20000,
			[
				'load.events',
			],
			True,
		)

	def _queue (self):
		return graph(
			self.monitor,
			'Queued URL for classification',
			20000,
			[
				'queue.size',
			],
			True,
		)

	def _workers (self):
		form = '<form action="/control/workers/commit" method="get">%s: <input type="text" name="%s" value="%s"><input type="submit" value="Submit"></form>'

		change = {
			'exaproxy.redirector.minimum' : self.supervisor.manager.low,
			'exaproxy.redirector.maximum' : self.supervisor.manager.high,
		}

		forms = []
		for name in ('exaproxy.redirector.minimum', 'exaproxy.redirector.maximum'):
			value = change[name]
			forms.append(form % (name,name,value))
		return '<pre style="margin-left:40px;">\n' + '\n'.join(forms)

	def _run (self):
		s  = '<pre style="margin-left:40px;">'
		s += '<form action="/control/debug/eval" method="get">eval <textarea type="text" name="python" cols="100" rows="10"></textarea><input type="submit" value="Submit"></form>'
		s += '<form action="/control/debug/exec" method="get">exec <textarea type="text" name="python" cols="100" rows="10"></textarea><input type="submit" value="Submit"></form>'
		return s

	def _logs (self):
		return 'do not view this in a web browser - the input is not sanitised, you have been warned !\n\n' + '\n'.join(History().formated())

	def _email (self,args):
		if self.email_sent:
			return '<center><b>You can only send one email per time ExaProxy is started</b></center>'
		self.email_sent, message = mail.send(args)
		return message

	def _json_running (self):
		return json.dumps(self.monitor.seconds[-1],sort_keys=True,indent=2,separators=(',', ': '))

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
			if path not in ('/json','/json/running','/json/configuration','/control/workers/commit','/control/debug/eval','/control/debug/exec'):
				return menu('<center><b>invalid url</b></center>')
			sections = path[1:].split('/') + ['']
		else:
			sections = path[1:-5].split('/') + ['']

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
			if subsection == 'logs':
				return self._logs()
			return menu(index)

		if section == 'performance':
			if subsection == 'processes':
				return menu(self._processes())
			if subsection == 'connections':
				return menu(self._connections())
			if subsection == 'servers':
				return menu(self._servers())
			if subsection == 'clients':
				return menu(self._clients())
			if subsection == 'transfered':
				return menu(self._transfer())
			if subsection == 'loops':
				return menu(self._loops())
			if subsection == 'events':
				return menu(self._events())
			if subsection == 'queue':
				return menu(self._queue())
			return menu(index)

		if section == 'control':
			action = (sections + [None,]) [2]

			if subsection == 'debug':
				if not self.supervisor.configuration.web.debug:
					return menu('not enabled')

				if action == 'exec':
					if '=' in args:
						try:
							key,value = args.split('=',1)
							self.log.critical('PYTHON CODE RAN : %s' % value)
							command = unquote(value.replace('+',' '))
							code = compile(command,'<string>', 'exec')
							exec code
							return 'done !'
						except Exception,e:
							return 'failed to run : \n' + command + '\n\nreason : \n' + str(type(e)) + '\n' + str(e)

				if action == 'eval':
					if '=' in args:
						try:
							key,value = args.split('=',1)
							self.log.critical('PYTHON CODE RAN : %s' % value)
							command = unquote(value.replace('+',' '))
							return str(eval(command))
						except Exception,e:
							return 'failed to run : \n' + command + '\n\nreason : \n' + str(type(e)) + '\n' + str(e)

				return menu(self._run())

			if subsection == 'workers':
				if action == 'commit':
					if '=' in args:
						key,value = args.split('=',1)

						if key == 'exaproxy.redirector.minimum':
							if value.isdigit():  # this prevents negative values
								setting = int(value)
								if setting > self.supervisor.manager.high:
									return menu(self._workers() + '<div style="color: red; padding-top: 3em;">value is higher than exaproxy.redirector.maximum</div>')
								self.supervisor.manager.low = setting
								return menu(self._workers() + '<div style="color: green; padding-top: 3em;">changed successfully</div>')

						if key == 'exaproxy.redirector.maximum':
							if value.isdigit():
								setting = int(value)
								if setting < self.supervisor.manager.low:
									return menu(self._workers() + '<div style="color: red; padding-top: 3em;">value is lower than exaproxy.redirector.minimum</div>')
								self.supervisor.manager.high = setting
								return menu(self._workers() + '<div style="color: green; padding-top: 3em;">changed successfully</div>')

						return menu(self._workers() + '<div style="color: red; padding-top: 3em;">invalid request</div>')

				return menu(self._workers())

			return menu(index)

		if section == 'about':
			if subsection == 'email':
				if args:
					return menu(self._email(args))
				return menu(mail.form)
			if subsection == 'licence':
				return menu(licence)
			return menu(index)

		if section == 'humans':
			return menu(humans.html)
		return menu(index)
