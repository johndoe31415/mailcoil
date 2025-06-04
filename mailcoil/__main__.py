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

import sys
import getpass
import mailcoil
from mailcoil.FriendlyArgumentParser import FriendlyArgumentParser

class CLIMailer():
	def __init__(self, args):
		self._args = args

	def _get_username_password(self):
		if self._args.auth_username is None:
			return (None, None)

		if self._args.auth_password is None:
			password = getpass.getpass()
		else:
			with open(self._args.auth_password) as f:
				password = f.read().rstrip("\r\n")
		return (self._args.auth_username, password)

	def run(self):
		mail = mailcoil.Email(from_address = getattr(self._args, "from"), wrap_text = self._args.wrap_text)
		if self._args.subject:
			mail.subject = self._args.subject

		mail.to(*self._args.to)
		mail.cc(*self._args.cc)
		mail.bcc(*self._args.bcc)

		if self._args.text is not None:
			with open(self._args.text) as f:
				mail.text = f.read()

		if self._args.html is not None:
			with open(self._args.html) as f:
				mail.html = f.read()

		for filename in self._args.attach_file:
			mail.attach(filename)
		for filename in self._args.attach_file_inline:
			mail.attach(filename, inline = True)

		if (self._args.smime_sign is not None) or (len(self._args.smime_encrypt) > 0):
			mail.security = mailcoil.CMS()
			if (self._args.smime_sign is not None):
				mail.security.sign(signer_certfile = self._args.smime_sign["cert"], signer_keyfile = self._args.smime_sign["key"], ca_certfile = self._args.smime_sign.get("ca"))
			mail.security.encrypt(*self._args.smime_encrypt)

		if self._args.smtp_server_uri is None:
			print(mail.serialize().content)
		else:
			dropoff = mailcoil.MailDropoff.parse_uri(self._args.smtp_server_uri)
			(username, password) = self._get_username_password()
			if username is not None:
				dropoff.username = username
				dropoff.password = password
			dropoff.post(mail)

def main():
	def sign_params(text):
		split_text = text.split(":")
		if len(split_text) == 2:
			return { "cert": split_text[0], "key": split_text[1] }
		elif len(split_text) == 3:
			return { "cert": split_text[0], "key": split_text[1], "ca": split_text[2] }
		else:
			raise ValueError(f"Only two or three arguments supported: {text}")

	parser = FriendlyArgumentParser(description = f"Simple command line tool to demonstrate Mailcoil v{mailcoil.VERSION}")
	parser.add_argument("-u", "--smtp-server-uri", metavar = "uri", help = "SMTP server dropoff in URI format. E.g., 'smtp://127.0.0.1', or 'smtps://mail.gmx.net:1122'. If omitted, just prints the mail on the command line.")
	parser.add_argument("-U", "--auth-username", metavar = "username", help = "Authenticate against SMTP server using this username.")
	parser.add_argument("--auth-password", metavar = "filename", help = "When using authentication, read the password from this file. Otherwise, password is requested on the command line.")
	parser.add_argument("-f", "--from", metavar = "email", required = True, help = "From address. Mandatory argument.")
	parser.add_argument("-s", "--subject", metavar = "text", help = "Text to use as subject.")
	parser.add_argument("-t", "--to", metavar = "email", action = "append", default = [ ], help = "Send email to this address in the 'To' field. May be specified multiple times.")
	parser.add_argument("-c", "--cc", metavar = "email", action = "append", default = [ ], help = "Send email to this address in the 'CC' field. May be specified multiple times.")
	parser.add_argument("-b", "--bcc", metavar = "email", action = "append", default = [ ], help = "Send email to this address in the 'BCC' field. May be specified multiple times.")
	parser.add_argument("-T", "--text", metavar = "filename", help = "Use the data in this text file as text content.")
	parser.add_argument("-H", "--html", metavar = "filename", help = "Use the data in this text file as HTML content.")
	parser.add_argument("--wrap-text", action = "store_true", help = "Wrap text content after 72 columns.")
	parser.add_argument("-a", "--attach-file", metavar = "filename", action = "append", default = [ ], help = "Attach this file to your email. May be specified multiple times.")
	parser.add_argument("--attach-file-inline", metavar = "filename", action = "append", default = [ ], help = "Attach this file to your email with Content-Disposition \"inline\". May be specified multiple times.")
	parser.add_argument("--smime-sign", type = sign_params, metavar = "cert:key[:ca_cert]", help = "Sign email using CMS (often referred to as \"S/MIME\"). Requires at least two filenames, one for the PEM-encoded key and the other for the cert.")
	parser.add_argument("--smime-encrypt", metavar = "cert", action = "append", default = [ ], help = "Encrypt email using CMS (often referred to as \"S/MIME\"). Requires the certificate file of the intended recipient. Can be specified multiple times to encrypt email for multiple recipients.")
	parser.add_argument("-v", "--verbose", action = "count", default = 0, help = "Increases verbosity. Can be specified multiple times to increase.")
	args = parser.parse_args(sys.argv[1:])

	cli_mailer = CLIMailer(args)
	cli_mailer.run()
	return 0

if __name__ == "__main__":
	sys.exit(main())
