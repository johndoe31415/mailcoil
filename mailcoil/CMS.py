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

import io
import enum
import subprocess
import email.parser

class CMS():
	class HashFunction(enum.Enum):
		sha1 = "sha1"
		sha256 = "sha256"
		sha384 = "sha384"
		sha512 = "sha512"
		sha3_256 = "sha3-256"
		sha3_384 = "sha3-384"
		sha3_512 = "sha3-512"

	class Cipher(enum.Enum):
		AES128 = "aes128"
		AES256 = "aes256"

	def __init__(self, openssl_binary: str = "openssl", hashfnc: HashFunction = HashFunction.sha256, cipher: Cipher = Cipher.AES256):
		self._openssl_binary = openssl_binary
		self._hashfnc = hashfnc
		self._cipher = cipher
		self._signer_certfile = None
		self._signer_keyfile = None
		self._signer_keyform = None
		self._detach_signature = True
		self._ca_certfile = None
		self._encrypt_recipient_certfiles = [ ]

	def sign(self, signer_certfile: str, signer_keyfile: str, ca_certfile: str | None = None, keyform: str = "pem", detach_signature: bool = True):
		self._signer_certfile = signer_certfile
		self._signer_keyfile = signer_keyfile
		self._ca_certfile = ca_certfile
		self._signer_keyform = keyform
		self._detach_signature = detach_signature
		return self

	def encrypt(self, *recipient_certfiles: tuple[str]):
		self._encrypt_recipient_certfiles += recipient_certfiles
		return self

	def _encrypt(self, message: bytes):
		cmd = [ self._openssl_binary, "cms", "-encrypt" ]
		cmd += [ f"-{self._cipher.value}" ]
		cmd += self._encrypt_recipient_certfiles
		return subprocess.check_output(cmd, input = message)

	def _sign(self, message: bytes):
		cmd = [ self._openssl_binary, "cms", "-sign" ]
		cmd += [ "-signer", self._signer_certfile ]
		if not self._detach_signature:
			cmd += [ "-nodetach" ]
		cmd += [ "-inkey", self._signer_keyfile, "-keyform", self._signer_keyform ]
		cmd += [ "-md", self._hashfnc.value ]
		if self._ca_certfile is not None:
			cmd += [ "-certfile", self._ca_certfile ]
		return subprocess.check_output(cmd, input = message)

	def process(self, msg: "MIMEBase"):
		# Order of operations in S/MIME is AtE.
		if self._signer_keyfile is not None:
			# Sign
			msg = self._sign(bytes(msg))
		if len(self._encrypt_recipient_certfiles) > 0:
			# Encrypt
			msg = self._encrypt(bytes(msg))

		# Then parse
		f = io.BytesIO(msg)
		msg = email.parser.BytesParser().parse(f)
		return msg
