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
		%s
		<br/>
		%s
		<br/>
	</body>
</html>

""" % (title,color,header,image,menu,text)


_menu = """\
<style type="text/css" media="screen">
	.droplinebar{
		overflow: hidden;
	}

	.droplinebar ul{
		margin: 0;
		padding: 0;
		float: left;
		width: 100%;
		font: bold 13px Arial;
		background: #242c54 center center repeat-x; /*default background of menu bar*/
	}

	.droplinebar ul li{
		display: inline;
	}

	.droplinebar ul li a{
		float: left;
		color: white;
		padding: 9px 11px;
		text-decoration: none;
	}

	.droplinebar ul li a:visited{
		color: white;
	}

	.droplinebar ul li a:hover, .droplinebar ul li .current{ /*background of main menu bar links onMouseover*/
		color: white;
	}

	/* Sub level menus*/
	.droplinebar ul li ul{
		position: absolute;
		z-index: 100;
		left: 0;
		top: 0;
		background: #303c76; /*sub menu background color */
		visibility: hidden;
	}

	/* Sub level menu links style */
	.droplinebar ul li ul li a{
		font: normal 13px Verdana;
		padding: 6px;
		padding-right: 8px;
		margin: 0;
		border-bottom: 1px solid navy;
	}

	.droplinebar ul li ul li a:hover{ /*sub menu links' background color onMouseover */
		background: #242c54;
	}
</style>

<script type="text/javascript" src="http://ajax.googleapis.com/ajax/libs/jquery/1.3.2/jquery.min.js"></script>

<script type="text/javascript">
	/*********************
	//* jQuery Drop Line Menu- By Dynamic Drive: http://www.dynamicdrive.com/
	//* Last updated: May 9th, 11'
	//* Menu avaiable at DD CSS Library: http://www.dynamicdrive.com/style/
	*********************/

	var droplinemenu={

		animateduration: {over: 200, out: 100}, //duration of slide in/ out animation, in milliseconds

		buildmenu:function(menuid){
			jQuery(document).ready(function($){
				var $mainmenu=$("#"+menuid+">ul")
				var $headers=$mainmenu.find("ul").parent()
				$headers.each(function(i){
					var $curobj=$(this)
					var $subul=$(this).find('ul:eq(0)')
					this._dimensions={h:$curobj.find('a:eq(0)').outerHeight()}
					this.istopheader=$curobj.parents("ul").length==1? true : false
					if (!this.istopheader)
						$subul.css({left:0, top:this._dimensions.h})
					var $innerheader=$curobj.children('a').eq(0)
					$innerheader=($innerheader.children().eq(0).is('span'))? $innerheader.children().eq(0) : $innerheader //if header contains inner SPAN, use that
					$curobj.hover(
						function(e){
							var $targetul=$(this).children("ul:eq(0)")
							if ($targetul.queue().length<=1) //if 1 or less queued animations
								if (this.istopheader)
									$targetul.css({left: $mainmenu.position().left, top: $mainmenu.position().top+this._dimensions.h})
								if (document.all && !window.XMLHttpRequest) //detect IE6 or less, fix issue with overflow
									$mainmenu.find('ul').css({overflow: (this.istopheader)? 'hidden' : 'visible'})
								$targetul.dequeue().slideDown(droplinemenu.animateduration.over)
						},
						function(e){
							var $targetul=$(this).children("ul:eq(0)")
							$targetul.dequeue().slideUp(droplinemenu.animateduration.out)
						}
					) //end hover
				}) //end $headers.each()
				$mainmenu.find("ul").css({display:'none', visibility:'visible', width:$mainmenu.width()})
			}) //end document.ready
		}
	}

	//build menu with DIV ID="myslidemenu" on page:
	droplinemenu.buildmenu("mydroplinemenu");
</script>

<div id="mydroplinemenu" class="droplinebar">
<ul>
	<li><a href="/index.html">home</a></li>
	<li><a href="/information.html">information</a>
		<ul>
			<li><a href="/information/introspection/supervisor.html">introspection</a></li>
			<li><a href="/information/configuration.html">configuration</a></li>
			<li><a href="/information/statistics.html">statistics</a></li>
		</ul>
	</li>
	<li><a href="/performance.html">performance</a>
		<ul>
			<li><a href="/performance/processes.html">processes</a></li>
			<li><a href="/performance/connections.html">connections</a></li>
			<li><a href="/performance/clients.html">clients</a></li>
			<li><a href="/performance/servers.html">servers</a></li>
			<li><a href="/performance/transfered.html">transfered</a></li>
			<li><a href="/performance/loops.html">loops</a></li>
			<li><a href="/performance/events.html">events</a></li>
		</ul>
	</li>
	<li><a href="/performance.html">about</a>
		<ul>
			<li><a href="/about/email.html">about</a></li>
			<li><a href="/about/licence.html">licence</a></li>
		</ul>
	</li>
</ul>
</div>
"""

_title = 'ExaProxy Monitoring'
_image = '<a href="http://www.exa-networks.co.uk/" target="exa-networks">%s</a>' % png(logo)


class Menu (object):
	def __init__ (self,options,options_information,options_performance,options_about):
		self._html_root = html(_title,'','#9999FF',_image,_menu,'*string*').replace('%','%%').replace('*string*','%s')
		self._html_information = html(_title,'','#9999FF',_image,_menu,'*string*').replace('%','%%').replace('*string*','%s')
		self._html_performance = html(_title,'','#9999FF',_image,_menu,'*string*').replace('%','%%').replace('*string*','%s')
		self._html_about = html(_title,'','#9999FF',_image,_menu,'*string*').replace('%','%%').replace('*string*','%s')

	def root (self,page):
		return self._html_root % page

	def performance (self,page):
		return self._html_performance % page

	def information (self,page):
		return self._html_information % page

	def about (self,page):
		return self._html_about % page
