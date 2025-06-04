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

import enum
import urllib.parse
import smtplib

class MailDropoff():
	class Scheme(enum.Enum):
		LMTP = "lmtp"
		LMTP_STARTTLS = "lmtp+starttls"
		SMTP = "smtp"
		SMTPS = "smtps"
		SMTP_STARTTLS = "smtp+startls"

	_SCHEME_BY_NAME = { scheme.value: scheme for scheme in Scheme }

	def __init__(self, scheme: Scheme, host: str, port: int | None = None, username: str | None = None, password: str | None = None):
		self._scheme = scheme
		self._host = host
		if port is None:
			self._port = {
				self.Scheme.LMTP:			24,
				self.Scheme.LMTP_STARTTLS:	24,
				self.Scheme.SMTP:			25,
				self.Scheme.SMTPS:			465,
				self.Scheme.SMTP_STARTTLS:	25,
			}[self._scheme]
		else:
			self._port = port
		self._username = username
		self._password = password

	@classmethod
	def parse_uri(cls, uri: str):
		parsed = urllib.parse.urlparse(uri)
		if parsed.scheme not in cls._SCHEME_BY_NAME:
			raise ValueError(f"\"{parsed.scheme}\" is not a valid URI scheme, supported are: {', '.join(sorted(cls._SCHEME_BY_NAME))}")
		scheme = cls._SCHEME_BY_NAME[parsed.scheme]
		if ":" in parsed.netloc:
			(host, port) = parsed.netloc.split(":", maxsplit = 1)
			port = int(port)
		else:
			(host, port) = (parsed.netloc, None)
		return cls(scheme = scheme, host = host, port = port)

	@property
	def username(self):
		return self._username

	@username.setter
	def username(self, value: str):
		self._username = value

	@property
	def password(self):
		return self._password

	@password.setter
	def password(self, value: str):
		self._password = value

	def postall(self, mails: list["Email"]):
		conn_class = smtplib.SMTP_SSL if (self._scheme == self.Scheme.SMTPS) else smtplib.SMTP
		with conn_class(self._host, self._port) as conn:
			try:
				if self._scheme == self.Scheme.SMTP_STARTTLS:
					conn.starttls()
				if (self._username is not None) and (self._password is not None):
					conn.login(self._username, self._password)

				for mail in mails:
					serialized_mail = mail.serialize()
					conn.send_message(serialized_mail.content, to_addrs = serialized_mail.recipients)
			finally:
				conn.quit()

	def post(self, mail: "Email"):
		return self.postall([ mail ])

	def __str__(self):
		return f"MailDropoff<{self._scheme.value}: {self._host}:{self._port}>"
