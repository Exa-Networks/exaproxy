#!/usr/bin/env python
# encoding: utf-8
"""
web.py

Created by Thomas Mangin on 2012-02-08.
Copyright (c) 2012 Exa Networks. All rights reserved.
"""


import cgi
from .response import html,png
from .images import logo,thomas,david

_humans_txt = """\
/* TEAM */

  Slave Driver / Grand Visionary: Thomas Mangin
  Google+: https://plus.google.com/104241996506596749840

  Engineer Extraordinaire: David Farrar
  Google+: https://plus.google.com/108845019528954357090

/* Other contributors */
"""

_humans_html = """\
<b style="padding: 20px 20px 20px 20px;">/* TEAM */</b>
<br>
<br style="clear:both;"/>
<div style="float:left;margin-left:80px;margin-right:10px;">
<img width="100px" src="data:image/png;base64,%s"/>
</div>
<br>
Slave Driver / Grand Visionary
<br>
<a href="https://plus.google.com/104241996506596749840">Thomas Mangin</a>
<br style="clear:both;"/>

<div style="float:left;margin-left:80px;margin-right:10px;">
<img width="100px" src="data:image/png;base64,%s"/>
</div>
<br>
Engineer Extraordinaire
<br>
<a href="https://plus.google.com/108845019528954357090">David Farrar</a>
<br style="clear:both;"/>
<br>
<b style="padding: 20px 20px 20px 20px;">/* Other contributors */</b>
<br>
""" % (thomas,david)

def menu (menus):
		return """\
<style type="text/css">
	.menu {
		float:left;
		width:100%%;
		background:#fff;
		border-bottom:4px solid #000;
		overflow:hidden;
		position:relative;
	}

	.menu ul {
		clear:left;
		float:left;
		list-style:none;
		margin:0;
		padding:0;
		position:relative;
		left:50%%;
		text-align:center;
	}

	.menu ul li {
		font-family:Arial, Helvetica, sans-serif;
		font-weight:normal;
		display:block;
		float:left;
		list-style:none;
		margin:0;
		padding:0;
		position:relative;
		right:50%%;
	}

	.menu ul li a {
		display:block;
		margin:0 0 0 1px;
		padding:3px 10px;
		background:#aaa;
		color: white;
		text-decoration:none;
		line-height:1.3em;
	}

	.menu ul li a:visited {
	}

	.menu ul li a:hover, .menu ul li .current {
		color: #fff;
		background-color:#0b75b2;
	}
</style>

<div class="menu">
	<ul>
		%s
	</ul>
</div>
	""" % '\n'.join(['<li/><a href="%s">%s</a>' % _ for _ in [menus[k] for k in sorted(menus.keys())]])

options = {
	1 : ('/index.html',                 'License'),
	2 : ('/objects/supervisor.html',    'Introspection'),
	3 : ('/configuration/index.html',   'Configuration'),
	4 : ('/statistics/index.html',      'Statistics'),
	5 : ('/connections/index.html',     'Connections'),
	6 : ('/transfer/index.html',        'Transfer'),
	7 : ('/processes/index.html',       'Processes'),
	8 : ('/email/index.html',           'Email'),
}

_title = 'ExaProxy Monitoring'
_menu = menu(options)
_image = '<a href="http://www.exa-networks.co.uk/" target="exa-networks">%s</a>' % png(logo)
_html = html(_title,'','#00BB55',_image,_menu,'*string*').replace('%','%%').replace('*string*','%s')

_index = """\
<pre style="margin-left:40px;">
ExaProxy

Copyright (c) 2011-2011, Exa Networks Limited
Copyright (c) 2011-2011, Thomas Mangin
Copyright (c) 2011-2011, David Farrar

All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
</pre>
"""

_listing = """\
<style type="text/css">
	.object {
		width: 800px;
		margin-left: 20px;
	}
	.object a {
		display: inline-block;
		width: 150px;
		text-align: left;
		font: 10pt Arial;
		padding: 5px 5px 5px 10px;
		text-decoration: none;
		color: #444;
		background: #eee;
		border: 1px solid #e4e4e4;
		margin: 1px 1px 1px 1px;
	}
	.object a:hover {
		color: #222;
		background: #e5e5e5;
		border: 1px solid #ccc;
	}
	.object .value {
		display: inline-block;
		width: 600px;
		text-align: left;
		font: 10pt Arial;
		padding: 5px 5px 5px 5px;
		text-decoration: none;
		color: #111;
		background: #e5e5e5;
		border: 1px solid #ccc;
		margin: 1px 1px 1px 1px;
	}
</style>
<div class="object">
%s
</div>
"""""

_enum = """\
<style type="text/css">
	.enum {
		width: 800px;
		margin-left: 20px;
	}
	.enum .key {
		display: inline-block;
		width: 250px;
		text-align: left;
		font: 10pt Arial;
		padding: 5px 5px 5px 10px;
		text-decoration: none;
		color: #444;
		background: #eee;
		border: 1px solid #e4e4e4;
		margin: 1px 1px 1px 1px;
	}
	.enum .value {
		display: inline-block;
		width: 500px;
		text-align: left;
		font: 10pt Arial;
		padding: 5px 5px 5px 0px;
		text-decoration: none;
		color: #111;
		background: #e5e5e5;
		border: 1px solid #ccc;
		margin: 1px 1px 1px 1px;
	}
</style>
<div class="enum">
%s
</div>
"""""

_chart = """\
<script language="javascript" type="text/javascript">setTimeout("location.reload();",%d);</script>
<script type="text/javascript" src="https://www.google.com/jsapi"></script>
<script type="text/javascript">
	google.load("visualization", "1", {packages:["corechart"]});
	google.setOnLoadCallback(drawChart);
	function drawChart() {
		var data = new google.visualization.DataTable();
%s
		data.addRows([
%s
		]);

		var options = {
			width: 800, height: 600,
			title: '%s',
			legend : {
				position: 'right',
				textStyle: {color: 'black', fontSize: 10}
			},
		};

		var chart = new google.visualization.LineChart(document.getElementById('chart_div'));
		chart.draw(data, options);
	}
</script>
<div id="chart_div"></div>
"""

_email = """\
<style type="text/css">
	.indented {
		margin-left: 20px;
	}
	.contact {
		background-color: #f3f3f3;
		border: solid 1px #a1a1a1;
		padding: 10px;
		width: 600px;
	}

	.contact label {
		display: block;
		width: 100px;
		float: left;
		margin-bottom: 10px;
	}

	.contact input {
		display: block;
		width: 430px;
		float: left;
		margin-bottom: 10px;
	}

	.contact label {
		text-align: right;
		padding-right: 20px;
	}

	.contact #message {
		display: block;
		width: 550px;
		height: 300px;
		float: left;
		margin-bottom: 10px;
	}

	.contact #submit {
		display: block;
		width: 50px;
		margin-bottom: 10px;
	}

	br {
		clear: left;
	}
</style>

<form action="/email/index.html" method="get">
	<div class="indented">
		<div class="contact">
			<label>Title</label>
			<select name="title">
				<option>Mr.</option>
				<option>Dr.</option>
				<option>Ms.</option>
				<option>Mrs.</option>
			</select><br>

			<label>First Name</label>
			<input id="firstname" name="firstname"><br>

			<label>Last Name</label>
			<input id="lastname" name="lastname"><br>

			<label>Employer</label>
			<input id="employer" name="employer"><br>

			<label>Email</label>
			<input id="email" name="email"><br>

			<textarea id="message" name="message" onFocus="if (this.value == this.defaultValue) { this.value = ''; }">
Hello,

ExaProxy is provided under the very permissive BSD license, so it is near impossible for us to know who is using it. Therefore we would very much appreciate if you could let us know what you are using ExaProxy for.

Please feel free to contact us if you have any questions, we are a very nice bunch (really :D), and will do our best to help you.

Yours sincerely,

The ExaProxy's Team.

PS: ExaProxy will stop answering HTTP requests while it sends the email. Only one mail can be sent using this form per time ExaProxy is run. This limit is here to prevent spammers and/or webcrawlers from causing isues. We do not recommand leaving the web interface open to the world.


			</textarea><br>
			<br>
			<input id="submit" type="submit" value="Submit" />
			<br>
		</div>
	</div>
</form>
"""

class Page (object):

	def __init__(self,monitor):
		self.monitor = monitor
		self.email_sent = False

	def _page (self,message):
		return _html % message

	def _introspection (self,objects):
		introduction = "<div style='padding: 10px 10px 10px 10px; font-weight:bold;'>Looking at the internal of ExaProxy for %s </div><br/>\n" % cgi.escape('.'.join(objects))
		link = cgi.escape('/'.join(objects[:-1])) if objects[:-1] else 'supervisor'
		line = ['<a href="/objects/%s.html">Back to parent object</a><br/>' % link]
		for k,content in self.monitor.introspection(objects):
			link = '/objects/%s.html' % cgi.escape('%s/%s' % ('/'.join(objects),k))
			line.append('<a href="%s">%s</a><span class="value">%s</span><br/>' % (link,k,cgi.escape(content)))
		return introduction + _listing % ('\n'.join(line))

	def _configuration (self):
		introduction = "<div style='padding: 10px 10px 10px 10px; font-weight:bold;'>ExaProxy Configuration</div><br/>\n"
		line = []
		for k,v in sorted(self.monitor.configuration().items()):
			line.append('<span class="key">%s</span><span class="value">&nbsp; %s</span><br/>' % (k,cgi.escape(v)))
		return introduction + _enum % ('\n'.join(line))

	def _statistics (self):
		introduction = "<div style='padding: 10px 10px 10px 10px; font-weight:bold;'>ExaProxy Statistics</div><br/>\n"
		line = []
		for k,v in sorted(self.monitor.statistics().items()):
			line.append('<span class="key">%s</span><span class="value">&nbsp; %s</span><br/>' % (k,cgi.escape(v)))
		return introduction + _enum % ('\n'.join(line))


	def _graph (self,_title,_reload,_keys,cumulative=False):
		legend = "data.addColumn('number', 'Seconds');" + '\n'.join(["data.addColumn('number', '%s');" % _ for _ in _keys])

		nb_records = len(self.monitor.history)
		last = ['0']*len(_keys)

		chart = []
		index = self.monitor.nb_recorded - nb_records
		for values in self.monitor.history:
			if cumulative:
				new = [values[_] for _ in _keys]
				chart.append("[ %d, %s]" % (index, ','.join([str(max(0,long(n)-long(l))).rstrip('L') for (n,l) in zip(new,last)])))
				last = new
			else:
				chart.append("[ %d, %s]" % (index, ','.join([values[_] for _ in _keys])))
			index += 1

		if cumulative and chart:
			chart.pop(0)

		padding = []
		index = 0
		top = self.monitor.nb_recorded - nb_records
		while index < top:
			padding.append("[ %d, %s ]" % (index, ','.join(['0']*len(_keys))))
			index += 1
		values = ',\n'.join(padding + chart)

		return _chart % (_reload,legend,values,_title)

	def _connections (self):
		return self._graph(
			'Proxy Connections',
			30000,
			[
				'running.proxy.clients.number',
				'running.proxy.download.opening',
				'running.proxy.download.established',
				'running.proxy.download',
				]
		)

	def _processes (self):
		return self._graph(
			'Proxy Processes',
			30000,
			[
				'running.processes.forked',
				'running.processes.min',
				'running.processes.max',
			]
		)

	def _transfer (self):
		return self._graph(
			'Proxy Bytes Transfered / seconds',
			30000,
			[
				'running.transfer.request',
				'running.transfer.download',
			],
			True
		)

	def _email (self,args):
		import cgi
		import time
		from email.mime.text import MIMEText
		from email.Utils import formatdate
		from smtplib import SMTP,SMTPException

		if self.email_sent:
			return self._page('<center><b>You can only send one email per time ExaProxy is started</b></center>')
		answers = cgi.parse_qs(args)

		_from = answers.get('email',[None,])[0]
		_to = 'The ExaProxy Team <exaproxy@exa-networks.co.uk>'

		if not _from:
			return self._page('<center><b>A email address is required to make sure our mail server let this mail through<br/>(press back on your browser)</b></center>')
		if '@' not in _from:
			return self._page('<center><b>A valid email address is required to make sure our mail server let this mail through<br/>(press back on your browser)</b></center>')

		formated = dict((k,"%s" % ','.join(v)) for (k,v) in answers.items())

		employer = formated.pop('employer','')

		message = ""
		message += "%s %s %s" % (formated.pop('title',''), formated.pop('firstname','').capitalize(), formated.pop('lastname','-').upper())
		message += " from %s" % employer if employer else ""
		message += " said\n\n%s\n" % formated.pop('message','<unset>')

		msg = MIMEText(message)
		msg['Subject'] = 'ExaProxy Message'
		msg['From'] = _from
		msg['To'] = _to
		msg['Message-ID'] = 'DO-NOT-HAVE-ONE-AND-SPAMASSASSIN-COMPLAINS-%s' % time.time()
		msg['Date'] = formatdate(localtime=True)
		msg.preamble = 'ExaProxy Message'

		try:
			s = SMTP('mx.exa-networks.co.uk')
			s.sendmail(_from, [_to,], msg.as_string())
			s.quit()
			self.email_sent = True
			return self._page('<center><b>Email sent, thank you</b></center>')
		except (SMTPException,Exception),e:
			return self._page('<center><b>Could not send email</b></center><br>%s' % str(e))

	def html (self,path):
		if len(path) > 5000:
			return self._page('<center><b>path is too long</b></center>')

		if path == '/':
			path = '/index.html'
			args = ''
		elif '?' in path:
			path,args = path.split('?',1)
		else:
			args = ''

		if not path.endswith('.html'):
			if path != '/humans.txt':
				return self._page('<center><b>invalid extension</b></center>')
			return _humans_txt
		if not path.startswith('/'):
			return self._page('<center><b>invalid url</b></center>')

		sections = path[1:-5].split('/')
		if not sections[0]:
			return self._page(_index)
		command = sections[0]

		if command == 'index':
			return self._page(_index)
		if command == 'objects':
			return self._page(self._introspection(sections[1:]))
		if command == 'configuration':
			return self._page(self._configuration())
		if command == 'statistics':
			return self._page(self._statistics())
		if command == 'connections':
			return self._page(self._connections())
		if command == 'processes':
			return self._page(self._processes())
		if command == 'transfer':
			return self._page(self._transfer())
		if command == 'email':
			if args:
				return self._email(args)
			return self._page(_email)
		if command == 'humans':
			return self._page(_humans_html)
		return self._page('')
