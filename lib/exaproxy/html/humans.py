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

