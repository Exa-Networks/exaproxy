#!/usr/bin/env python
# encoding: utf-8
"""
email.py

Created by Thomas Mangin on 2012-02-25.
Copyright (c) 2012 Exa Networks. All rights reserved.
"""

import cgi
import time
from email.mime.text import MIMEText
from email.Utils import formatdate
from smtplib import SMTP,SMTPException


class mail (object):
	form = """\
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

	@staticmethod
	def send (args):
		answers = cgi.parse_qs(args)

		_from = answers.get('email',[None,])[0]
		_to = 'The ExaProxy Team <exaproxy@exa-networks.co.uk>'

		if not _from:
			return '<center><b>A email address is required to make sure our mail server let this mail through<br/>(press back on your browser)</b></center>'
		if '@' not in _from:
			return '<center><b>A valid email address is required to make sure our mail server let this mail through<br/>(press back on your browser)</b></center>'

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
			return '<center><b>Email sent, thank you</b></center>'
		except (SMTPException,Exception),e:
			return '<center><b>Could not send email</b></center><br>%s' % str(e)
