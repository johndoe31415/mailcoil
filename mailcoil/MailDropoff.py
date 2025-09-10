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

import datetime
import enum
import urllib.parse
import time
import smtplib
import imaplib
from .Exceptions import MaildropFailedException

class MailDropoff():
	class Scheme(enum.Enum):
		LMTP = "lmtp"
		LMTP_STARTTLS = "lmtp+starttls"
		SMTP = "smtp"
		SMTPS = "smtps"
		SMTP_STARTTLS = "smtp+startls"
		IMAP = "imap"
		IMAPS = "imaps"
		FILE = "file"

	_SCHEME_BY_NAME = { scheme.value: scheme for scheme in Scheme }

	def __init__(self, scheme: Scheme, host: str, port: int | None = None, username: str | None = None, password: str | None = None, path: str | None = None):
		self._scheme = scheme
		self._host = host
		if port is None:
			self._port = {
				self.Scheme.LMTP:			24,
				self.Scheme.LMTP_STARTTLS:	24,
				self.Scheme.SMTP:			25,
				self.Scheme.SMTPS:			465,
				self.Scheme.SMTP_STARTTLS:	25,
				self.Scheme.IMAP:			143,
				self.Scheme.IMAPS:			993,
				self.Scheme.FILE:			None,
			}[self._scheme]
		else:
			self._port = port
		self._username = username
		self._password = password
		self._path = path or ""
		if self._scheme != self.Scheme.FILE:
			self._path = self._path.lstrip("/")
		if self._path == "":
			self._path = None
		if (self._scheme in [ self.Scheme.IMAP, self.Scheme.IMAPS ]) and (self._path is None):
			raise ValueError("For storing an email on IMAP, you need to specify a mailbox folder as a path.")

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

		return cls(scheme = scheme, host = host, port = port, path = parsed.path)

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

	def _postall_smtp(self, mails: list["Email"]):
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

	def _postall_imap(self, mails: list["Email"]):
		conn_class = imaplib.IMAP4_SSL if (self._scheme == self.Scheme.IMAPS) else imaplib.IMAP4
		with conn_class(self._host, self._port) as conn:
			try:
				if (self._username is not None) and (self._password is not None):
					try:
						conn.login(self._username, self._password)
					except imaplib.IMAP4.error as e:
						raise MaildropFailedException(f"Login to {self._scheme.name} server {self._host}:{self._port} failed: {str(e)}") from e
				else:
					raise MaildropFailedException("IMAP delivery requires authentication.")

				(status, imap_rsp) = conn.select(mailbox = self._path)
				if status != "OK":
					raise MaildropFailedException(f"No such IMAP mailbox \"{self._path}\" on {self._host}:{self._port}: {str(imap_rsp)}")

				for mail in mails:
					serialized_mail = mail.serialize()
					imap_date_time = imaplib.Time2Internaldate(time.time())
					(status, imap_rsp) = conn.append(mailbox = self._path, flags = None, date_time = imap_date_time, message = bytes(serialized_mail.content))
					if status != "OK":
						raise MaildropFailedException(f"Unable to append message to \"{self._path}\" on {self._host}:{self._port}: {str(imap_rsp)}")
			finally:
				conn.logout()

	def _postall_file(self, mails: list["Email"]):
		post_date = datetime.datetime.now().strftime("%a %b %d %H:%M:%S %Y")
		with open(self._path, "a") as f:
			for mail in mails:
				print(f"From - {post_date}", file = f)
				print("X-Mozilla-Status: 0000", file = f)
				serialized_mail = mail.serialize()
				f.write(bytes(serialized_mail.content).decode("utf-8"))
				print(file = f)

	def postall(self, mails: list["Email"]):
		if self._scheme in [ self.Scheme.LMTP, self.Scheme.LMTP_STARTTLS, self.Scheme.SMTP, self.Scheme.SMTPS, self.Scheme.SMTP_STARTTLS ]:
			return self._postall_smtp(mails)
		elif self._scheme in [ self.Scheme.IMAP, self.Scheme.IMAPS ]:
			return self._postall_imap(mails)
		elif self._scheme == self.Scheme.FILE:
			return self._postall_file(mails)
		else:
			raise NotImplementedError(self._scheme)

	def post(self, mail: "Email"):
		return self.postall([ mail ])

	def __str__(self):
		return f"MailDropoff<{self._scheme.value}: {self._host}:{self._port}>"
