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

import os
import email
import time
import textwrap
import dataclasses
import mimetypes
import email.policy
import mailcoil
from .Exceptions import NoRecipientException, NoBodyException

@dataclasses.dataclass
class MailAddress():
	mail: str
	name: str | None = None

	def encode(self):
		if self.name is not None:
			return email.utils.formataddr((self.name, self.mail))
		else:
			return self.mail

	@classmethod
	def parse(cls, addr: "MailAddress | str"):
		if isinstance(addr, cls):
			return addr
		elif isinstance(addr, dict):
			return MailAddress(mail = addr.get("mail"), name = addr.get("name"))
		else:
			(name, mail) = email.utils.parseaddr(addr)
			if name == "":
				return cls(mail = mail)
			else:
				((name_bindata, encoding), ) = email.header.decode_header(name)
				if encoding is None:
					return cls(mail = mail, name = name)
				else:
					return cls(mail = mail, name = name_bindata.decode(encoding))

	@classmethod
	def parsemany(cls, addrs: str):
		return [ cls.parse(addr) for addr in addrs.split(",") ]

@dataclasses.dataclass
class SerializedEmail():
	recipients: list[str]
	content: bytes

@dataclasses.dataclass(slots = True)
class Attachment():
	data: bytes
	maintype: str
	subtype: str
	filename: str
	inline: bool
	content_id: str

class Email():
	def __init__(self, from_address: MailAddress | str, subject: str | None = None, text: str | None = None, wrap_text: bool = False, html: str | None = None, security: "SMIME | None" = None):
		self._from = MailAddress.parse(from_address)
		self._to = [ ]
		self._cc = [ ]
		self._bcc = [ ]
		self._subject = subject
		self._text = text
		self._wrap_text = wrap_text
		self._html = html
		self._security = security
		self._datetime = time.time()
		self._message_id = f"<{os.urandom(16).hex()}@mailcoil>"
		self._attachments = [ ]
		self._user_agent = None

	@property
	def recipient_count(self):
		return len(self._to) + len(self._cc) + len(self._bcc)

	def to(self, *mail_addresses: tuple[MailAddress | str]):
		self._to += [ MailAddress.parse(addr) for addr in mail_addresses ]
		return self

	def cc(self, *mail_addresses: tuple[MailAddress | str]):
		self._cc += [ MailAddress.parse(addr) for addr in mail_addresses ]
		return self

	def bcc(self, *mail_addresses: tuple[MailAddress | str]):
		self._bcc += [ MailAddress.parse(addr) for addr in mail_addresses ]
		return self

	@property
	def user_agent(self):
		return self._user_agent

	@user_agent.setter
	def user_agent(self, value: str):
		self._user_agent = value

	@property
	def subject(self):
		return self._subject

	@subject.setter
	def subject(self, value: str):
		self._subject = value

	@property
	def text(self):
		return self._text

	@text.setter
	def text(self, value: str):
		self._text = value

	@property
	def html(self):
		return self._html

	@html.setter
	def html(self, value: str):
		self._html = value

	@property
	def wrapped_text(self):
		if self._wrap_text:
			return self._wrap_paragraphs(self.text)
		else:
			return self.text

	@property
	def security(self):
		return self._security

	@security.setter
	def security(self, value: str):
		self._security = value

	def _mimetype(self, filename: str, override: str | None):
		if override is None:
			(mimetype, _) = mimetypes.guess_type(filename)
			if mimetype is None:
				return "application/octet-stream"
			else:
				return mimetype
		else:
			return override

	def attach_data(self, data: bytes, filename: str, mimetype: str | None = None, inline: bool = False, cid: str | None = None):
		(maintype, subtype) = self._mimetype(filename, mimetype).split("/")
		content_id = f"cid{len(self._attachments)}" if (cid is None) else cid
		attachment = Attachment(data = data, maintype = maintype, subtype = subtype, filename = filename, inline = inline, content_id = content_id)
		self._attachments.append(attachment)
		return f"cid:{attachment.content_id}"

	def attach(self, filename: str, mimetype: str | None = None, shown_filename: str | None = None, inline: bool = False, cid: str | None = None):
		with open(filename, "rb") as f:
			data = f.read()
		if shown_filename is None:
			shown_filename = os.path.basename(filename)
		return self.attach_data(data, filename = shown_filename, mimetype = mimetype, inline = inline, cid = cid)

	@staticmethod
	def _wrap_paragraphs(text: str) -> str:
		wrapped = [ ]
		for paragraph in text.split("\n"):
			parwrapped = textwrap.wrap(paragraph, width = 72)
			if len(parwrapped) == 0:
				parwrapped = [ "" ]
			wrapped += parwrapped
		return "\n".join(wrapped)


	def _layer_text_content(self):
		if self.recipient_count == 0:
			raise NoRecipientException("Mail has no To, CC, or BCC set. Unable to serialize.")

		if (self.text is None) and (self.html is None):
			raise NoBodyException("Mail has no text or HTML content.")

		msg = email.message.EmailMessage()

		if (self.text is not None) and (self.html is not None):
			# text and HTML as multipart/alternative
			msg.set_content(self.wrapped_text, subtype = "plain")
			msg.add_alternative(self.html, subtype = "html")
		elif self.html is None:
			msg.set_content(self.wrapped_text, subtype = "plain")
		else:
			# HTML only
			msg.set_content(self.html, subtype = "html")
		return msg

	def _layer_attachments(self, msg: "EmailMessage"):
		for attachment in self._attachments:
			if not attachment.inline:
				msg.add_attachment(attachment.data, maintype = attachment.maintype, subtype = attachment.subtype, filename = attachment.filename)
			else:
				msg.add_attachment(attachment.data, maintype = attachment.maintype, subtype = attachment.subtype, filename = attachment.filename, disposition = "inline", cid = attachment.content_id)
		return msg

	def _layer_security(self, prev_layer: "EmailMessage"):
		if self._security is None:
			msg = prev_layer
		else:
			msg = self._security.process(prev_layer)
		return msg

	def serialize(self):
		msg = self._layer_text_content()
		msg = self._layer_attachments(msg)
		msg = self._layer_security(msg)

		if self._subject is not None:
			msg["Subject"] = self._subject
		msg["Message-ID"] = self._message_id
		msg["Date"] = email.utils.formatdate(self._datetime, localtime = True)
		if self.user_agent is None:
			msg["User-Agent"] = f"mailcoil v{mailcoil.VERSION}"
		else:
			msg["User-Agent"] = f"{self.user_agent} via mailcoil v{mailcoil.VERSION}"
		msg["From"] = self._from.encode()
		if len(self._to) > 0:
			msg["To"] = ", ".join([address.encode() for address in self._to ])
		if len(self._cc) > 0:
			msg["CC"] = ", ".join([address.encode() for address in self._cc ])
		if len(self._bcc) > 0:
			msg["BCC"] = ", ".join([address.encode() for address in self._bcc ])
		return SerializedEmail(content = msg, recipients = [ addr.mail for addr in (self._to + self._cc + self._bcc) ])

	def to_dict(self):
		msg = {
			"date": self._datetime,
			"message_id": self._message_id,
			"from": dataclasses.asdict(self._from),
			"to": [ dataclasses.asdict(addr) for addr in self._to ],
		}
		if self.subject is not None:
			msg["subject"] = self.subject
		if len(self._cc) > 0:
			msg["cc"] = [ dataclasses.asdict(addr) for addr in self._cc ]
		if len(self._bcc) > 0:
			msg["bcc"] = [ dataclasses.asdict(addr) for addr in self._bcc ]
		if self._text is not None:
			msg["text"] = self._text
		if self._html is not None:
			msg["html"] = self._html
		return msg

	def __format__(self, fmt_str: str):
		if self.subject is None:
			text = "-no subject-"
		else:
			text = f"\"{self.subject}\""
		text += f" from {self._from.mail}"
		text += f" to {', '.join(mail.mail for mail in self._to)}"
		return text
