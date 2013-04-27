# encoding: utf-8
"""
humans.py

Created by Thomas Mangin on 2012-02-25.
Copyright (c) 2011-2013 Exa Networks. All rights reserved.
"""

from .images import thomas,david

class humans:
	txt = """\
/* TEAM */

  Slave Driver / Grand Visionary: Thomas Mangin
  Google+: https://plus.google.com/104241996506596749840

  Engineer Extraordinaire: David Farrar
  Google+: https://plus.google.com/108845019528954357090

/* Other contributors */
"""

	html = """\
<div style="padding: 20px 20px 20px 20px;">
	<b>/* TEAM */</b><br/>
	<br/>
	<div style="margin-left:20px;margin-right:10px;">
		<img width="100px" src="data:image/png;base64,%s"/>
	</div>
	<br/>
	Slave Driver / Grand Visionary<br/>
	<a href="https://plus.google.com/104241996506596749840">Thomas Mangin</a><br/>
	<br/>

	<div style="margin-left:20px;margin-right:10px;">
		<img width="100px" src="data:image/png;base64,%s"/>
	</div>
	<br/>
	Engineer Extraordinaire<br/>
	<a href="https://plus.google.com/108845019528954357090">David Farrar</a><br/>
</div>
<div style="padding: 20px 20px 20px 20px;">
	<b>/* Other contributors */</b>
	<br/>
</div>
""" % (thomas,david)
