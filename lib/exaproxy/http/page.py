#!/usr/bin/env python
# encoding: utf-8
"""
web.py

Created by Thomas Mangin on 2012-02-08.
Copyright (c) 2012 Exa Networks. All rights reserved.
"""


import cgi
from .response import html,image

_humans = """\
/* TEAM */
  Grand Visionary: Thomas Mangin
  Google+: https://plus.google.com/104241996506596749840

  Engineer Extraordinaire: David Farrar
  Google+: https://plus.google.com/108845019528954357090

/* Other contributors */
"""


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
	1 : ('/index.html'                , 'Home'),
	2 : ('/objects/supervisor.html'   , 'Introspection'),
	3 : ('/configuration/index.html'  , 'Configuration'),
	4 : ('/statistics/index.html'     , 'Statistics'),
	5 : ('/connections/index.html'    , 'Connections'),
	6 : ('/processes/index.html'      , 'Processes'),
	7 : ('/transfer/index.html'       , 'Transfer'),
}

_title = 'ExaProxy Monitoring'
_menu = menu(options)
_image = '<a href="http://www.exa-networks.co.uk/" target="exa-networks">%s</a>' % image
_html = html(_title,'','#00BB55',_image,_menu,'*string*').replace('%','%%').replace('*string*','%s')

_index = """\
<center>
	<b>Welcome to ExaProxy Management web server.</b>
	<br/>
	<br/>
	Those pages are under development (this sentence brings me back to the 90's) :D.<br/>
	We intend to add here real time information about the Proxy and other nice things.<br>
</center>
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


class Page (object):
	
	def __init__(self,monitor):
		self.monitor = monitor

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


	def html (self,path):
		if len(path) > 200:
			return self._page('<center><b>path is too long</b></center>')
		if path == '/':
			path = '/index.html'
		if not path.endswith('.html'):
			if path != '/humans.txt':
				return self._page('<center><b>invalid extension</b></center>')
			return _humans
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
		return self._page('<center><b>are you looking for an easter egg ?</b></center>')
