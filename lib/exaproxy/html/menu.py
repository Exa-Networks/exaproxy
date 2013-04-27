# encoding: utf-8
"""
menu.py

Created by Thomas Mangin on 2012-02-25.
Copyright (c) 2011-2013 Exa Networks. All rights reserved.
"""

from .img import png
from .images import logo


def html (title,header,color='#FF0000',image=png(logo)):
	if header: header += '<br/>'
	return """\
<html>
	<head>
		<title>%s</title>
		<meta http-equiv="cache-control" content="no-cache">
	</head>
	<style type="text/css" media="screen">
		.vmenu {
			font-family: Verdana, Arial, Helvetica, sans-serif;
			font-size: 100%%%%;
			width: 160px;
			padding: 0px;
			margin: 0px 10px 0px 0px;
			border-left: 1px solid #000000;
			float: right;
		}
		.vmenu h1 {
			display: block;
			background-color:#F4F4F4;
			font-size: 90%%%%;
			padding: 13px 0px 5px 3px;
			color: #333333;
			margin: 0px;
			border-bottom: 1px solid #000000;
			width:159px;
		}
		.vmenu h1 a, .vmenu h1 a:hover, .vmenu h1 a:focus {
			color: #0000C3;
			text-decoration: none;
		}
		.vmenu ul {
			list-style: none;
			margin: 0px;
			padding: 0px;
			border: none;
		}
		.vmenu ul li {
			margin: 0px;
			padding: 0px;
		}
		.vmenu ul li a {
			font-size: 80%%%%;
			display: block;
			border-bottom: 1px dashed #004E9C;
			padding: 1px 0px 2px 20px;
			text-decoration: none;
			color: #666666;
			width: 142px;
		}
		.vmenu ul li a:hover, .vmenu ul li a:focus {
			color: #000000;
			background-color: #EEEEEE;
		}
	</style>
	<body leftmargin="0" topmargin="0" rightmargin="0" bgcolor="#FFFFFF" text="#000000" link="#0000FF" alink="#0000FF" vlink="#0000FF">
		<center>
			<div style="padding:15px; color: #FFFFFF; background: %s; font-size: 40px; font-family: verdana,sans-serif,arial; font-weight: bold; border-bottom: solid 1px #A0A0A0;">
				%s
				%s
			</div>
		</center>
<div style="float: left">
*text*
<br/>
<br/>
</div>
*menu*
	</body>
</html>

""" % (title,color,header,image)

_title = 'ExaProxy Monitoring'
_image = '<a href="http://www.exa-networks.co.uk/" target="exa-networks">%s</a>' % png(logo)


def Menu (options):
	menu = '<div class="vmenu">\n'
	menu += '\t<h1><a href="/index.html">Home</a></h1>\n'

	for name, url, section in options:
		menu += '\t<h1>%s</h1>\n' % (name)

		if section:
			menu += '\t<ul>\n'
			for name, url, new in section:
				if new:
					menu += '\t\t<li><a href="%s" target="%s">%s</a></li>\n' % (url,name,name)
				else:
					menu += '\t\t<li><a href="%s">%s</a></li>\n' % (url,name)
			menu += '\t</ul>\n'

	menu += '</div>\n'

	_html = html(_title,'','#9999FF',_image).replace('*text*','%s').replace('*menu*',menu)

	def _lambda (page):
		return _html % page

	return _lambda
