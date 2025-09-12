#	mailcoil - Effortless, featureful SMTP
#	Copyright (C) 2011-2025 Johannes Bauer
#
#	This file is part of mailcoil.
#
#	mailcoil is free software; you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation; this program is ONLY licensed under
#	version 3 of the License, later versions are explicitly excluded.
#
#	mailcoil is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.
#
#	You should have received a copy of the GNU General Public License
#	along with mailcoil; if not, write to the Free Software
#	Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
#	Johannes Bauer <JohannesBauer@gmx.de>
"""Package for easily creating and sending mails via SMTP or SMTPS.

For usage of mailcoil you first need to define a dropoff at which mails should
be posted. This is typically your MTA or smart relay:

	dropoff = mailcoil.MailDropoff(mailcoil.MailDropoff.Scheme.SMTPS, "smtp.my-server.com")

You then can create an email:

	mail = mailcoil.Email(from_address = "Johannes Bauer <johannes.bauer@gmx.de>", subject = "What's up?").to("someone@gmx.de")

CC and BCC are also supported using the same syntax as the `.to()` method:

	mail.cc("cc1@gmx.de", "cc2@gmx.de").bcc("bcc@gmx.de")

Emails can use text/plain, text/html, or both bodies:

	mail.text = "This is the text content!"
	mail.html = "<html><body><h1>Hey!</h1><p>This is the HTML content!</body></html>"

To attach files to this mail, simply you can use the `attach` method:

	mail.attach("foo.jpg")

By default, the Content-Disposition of attachments is "attachment". However,
you can also create "inline" attachments that you can then reuse in your HTML
portion, e.g.:

	src_cid = mail.attach("foo.jpg", inline = True)
	mail.html = f"<html><body><h1>Hey!</h1><p>This is the HTML content!<img src='${src_cid}'></body></html>"

By default, the Content-ID is auto-generated, which means that it depends on
the number of attachments. If you want fixed CIDs, you can also do that. Note
that You are then responsible for not creating collisions in the CIDs:

	src_cid = mail.attach("foo.jpg", inline = True, cid = "foobar")
	mail.html = f"<html><body><h1>Hey!</h1><p>This is the HTML content!<img src='cid:foobar'></body></html>"

If you wish to sign or encrypt mail using CMS (commonly known as S/MIME), you
need to set the security property of your email and configure it properly. For
example, for just signing, this works:

	mail.security = mailcoil.CMS().sign(signer_keyfile = "my_key.pem", signer_certfile = "my_cert.pem", ca_certfile = "my_ca.pem")

If you additionally want to encrypt for three different targets, you can also
do:

	mail.security.encrypt("target1.pem", "target2.pem", "target3.pem")

Similarly, you may also only encrypt without signing:

	mail.security = mailcoil.CMS().encrypt("target.pem")

When your mail is finally set up, you can drop it off at the previously defined
dropoff:

	dropoff.post(mail)

A complete example is therefore:

	import mailcoil
	dropoff = mailcoil.MailDropoff(mailcoil.MailDropoff.Scheme.SMTPS, "smtp.my-server.com")
	mail = mailcoil.Email(from_address = "Johannes Bauer <johannes.bauer@gmx.de>", subject = "What's up?").to("someone@gmx.de")
	mail.cc("cc1@gmx.de", "cc2@gmx.de").bcc("bcc@gmx.de")
	mail.text = "This is the text content!"

	# Attach file and use it in HTML portion
	src_cid = mail.attach("foo.jpg", inline = True)
	mail.html = f"<html><body><h1>Hey!</h1><p>This is the HTML content!<img src='${src_cid}'></body></html>"

	# Sign and encrypt
	mail.security = mailcoil.CMS().sign(signer_keyfile = "my_key.pem", signer_certfile = "my_cert.pem", ca_certfile = "my_ca.pem").encrypt("target1.pem", "target2.pem", "target3.pem")

	# Send mail through the dropoff
	dropoff.post(mail)

Another, shorter example, that showcases local debugging capabilities and will
write a local file /tmp/mailbox.txt that is compatible with Thunderbird:

	import mailcoil
	dropoff = mailcoil.MailDropoff.parse_uri("file:///tmp/mailbox.txt")
	mail = mailcoil.Email(from_address = "Johannes Bauer <johannes.bauer@gmx.de>", subject = "What's up?").to("someone@gmx.de")
	mail.text = "This is a test email."
	dropoff.post(mail)
"""

from .MailDropoff import MailDropoff
from .Email import Email, MailAddress
from .CMS import CMS
from .Exceptions import MailCoilException

VERSION = "0.0.5"
