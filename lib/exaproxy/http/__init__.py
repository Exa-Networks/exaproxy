# encoding: utf-8
"""
http.py

Created by Thomas Mangin on 2011-12-02.
Copyright (c) 2011-2013  Exa Networks. All rights reserved.
"""

#	destination = re.compile("(GET|POST|PUT|HEAD|DELETE|OPTIONS|TRACE|CONNECT)\s+(http://[^/]*|)(/?[^ \r]*)\s+(HTTP/.*\r?\nHost\s*:\s*)([^\r]*)(|\r?\n)", re.IGNORECASE)
#	x_forwarded_for = re.compile("(|\n)X-Forwarded-For: ?(((1?\d?\d)|(2([0-4]\d|5[0-5])))\.)(((1?\d?\d)|(2([0-4]\d|5[0-5])))\.)(((1?\d?\d)|(2([0-4]\d|5[0-5])))\.)((2([0-4]\d|5[0-5]))|(1?\d?\d))", re.IGNORECASE)

#450 Blocked by Windows Parental Controls
#A Microsoft extension. This error is given when Windows Parental Controls are turned on and are blocking access to the given webpage.
#598 Network read timeout error
#This status code is not specified in any RFCs, but is used by some[which?] HTTP proxies to signal a network read timeout behind the proxy to a client in front of the proxy.
#599 Network connect timeout error
#This status code is not specified in any RFCs, but is used by some[which?] HTTP proxies to signal a network connect timeout behind the proxy to a client in front of the proxy.
