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

import dataclasses
import email.header
import email.utils

@dataclasses.dataclass
class SerializedEmail():
	recipients: list[str]
	content: "email.Message"

	@property
	def subject(self):
		"""Returns best-effort decoding of the email subject (may not be
		possible if the raw message is malformed."""
		subject = self.content["Subject"]
		if subject is None:
			return None
		parts = email.header.decode_header(subject)
		decoded = [ ]
		for (raw_encoding, codec_name) in parts:
			if isinstance(raw_encoding, str):
				decoded.append(raw_encoding)
			else:
				decoded.append(raw_encoding.decode(codec_name or "utf-8", errors = "ignore"))
		return "".join(decoded)

	@property
	def from_addr(self):
		from_addr = self.content["From"]
		if from_addr is None:
			return None
		addresses = email.utils.getaddresses([ from_addr ])
		return addresses[0]
