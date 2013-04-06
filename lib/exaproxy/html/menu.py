# encoding: utf-8
"""
menu.py

Created by Thomas Mangin on 2012-02-25.
Copyright (c) 2011-2013 Exa Networks. All rights reserved.
"""

from .img import png
from .images import logo


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


def _menu (menus,submenus=None):
		menu_css = """\
<style type="text/css">
	.menu {
		float:left;
		width:100%;
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
		left:50%;
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
		right:50%;
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
"""

		menu = """
<div class="menu">
	<ul>
		%s
	</ul>
</div>
""" % '\n'.join(['<li/><a href="%s">%s</a>' % _ for _ in menus])

		if not submenus:
			return menu_css + menu

		submenu_css = """\
<style type="text/css">
	.submenu {
		float:left;
		width:100%;
		background:#fff;
		overflow:hidden;
		position:relative;
	}

	.submenu ul {
		clear:left;
		float:left;
		list-style:none;
		margin:0;
		padding:0;
		position:relative;
		left:50%;
		text-align:center;
	}

	.submenu ul li {
		font-family:Arial, Helvetica, sans-serif;
		font-weight:normal;
		display:block;
		float:left;
		list-style:none;
		margin:0;
		padding:0;
		position:relative;
		right:50%;
	}

	.submenu ul li a {
		display:block;
		margin:0 0 0 1px;
		padding:3px 10px;
		background:#aaa;
		color: white;
		text-decoration:none;
		line-height:1.3em;
	}

	.submenu ul li a:visited {
	}

	.submenu ul li a:hover, .submenu ul li .current {
		color: #fff;
		background-color:#0b75b2;
	}
</style>
"""

		submenu = """
<div class="submenu">
	<ul>
		%s
	</ul>
</div>
""" % '\n'.join(['<li/><a href="%s">%s</a>' % _ for _ in submenus])
		return menu_css + menu + submenu_css + submenu

_title = 'ExaProxy Monitoring'
_image = '<a href="http://www.exa-networks.co.uk/" target="exa-networks">%s</a>' % png(logo)


class Menu (object):
	def __init__ (self,options,options_information,options_performance,options_about):
		self._html_root = html(_title,'','#00BB55',_image,_menu(options,None),'*string*').replace('%','%%').replace('*string*','%s')
		self._html_information = html(_title,'','#00BB55',_image,_menu(options,options_information),'*string*').replace('%','%%').replace('*string*','%s')
		self._html_performance = html(_title,'','#00BB55',_image,_menu(options,options_performance),'*string*').replace('%','%%').replace('*string*','%s')
		self._html_about = html(_title,'','#00BB55',_image,_menu(options,options_about),'*string*').replace('%','%%').replace('*string*','%s')

	def root (self,page):
		return self._html_root % page

	def performance (self,page):
		return self._html_performance % page

	def information (self,page):
		return self._html_information % page

	def about (self,page):
		return self._html_about % page
