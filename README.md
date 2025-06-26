# mailcoil
Mailcoil is a small SMTP wrapper around Python's native functionality that
makes several tasks easier, namely constructing mails that contain referenced
inline attachments (e.g., images that are referenced from within HTML mail) or
signing/encrypting emails via CMS (commonly known as S/MIME). It also has
support for IMAP so that sent mails can be stored in a "Sent" folder using the
same mechanism as sending them through SMTP.

## Usage
For usage of mailcoil you first need to define a dropoff at which mails should
be posted. This is typically your MTA or smart relay:

```python3
dropoff = mailcoil.MailDropoff(mailcoil.MailDropoff.Scheme.SMTPS, "smtp.my-server.com")
```

You then can create an email:

```python3
mail = mailcoil.Email(from_address = "Johannes Bauer <johannes.bauer@gmx.de>", subject = "What's up?").to("someone@gmx.de")
```

CC and BCC are also supported using the same syntax as the `.to()` method:

```python3
mail.cc("cc1@gmx.de", "cc2@gmx.de").bcc("bcc@gmx.de")
```

Emails can use text/plain, text/html, or both bodies:

```python3
mail.text = "This is the text content!"
mail.html = "<html><body><h1>Hey!</h1><p>This is the HTML content!</body></html>"
```

To attach files to this mail, simply you can use the `attach` method:

```python3
mail.attach("foo.jpg")
```

By default, the Content-Disposition of attachments is "attachment". However,
you can also create "inline" attachments that you can then reuse in your HTML
portion, e.g.:

```python3
src_cid = mail.attach("foo.jpg", inline = True)
mail.html = f"<html><body><h1>Hey!</h1><p>This is the HTML content!<img src='${src_cid}'></body></html>"
```

By default, the Content-ID is auto-generated, which means that it depends on
the number of attachments. If you want fixed CIDs, you can also do that. Note
that You are then responsible for not creating collisions in the CIDs:

```python3
src_cid = mail.attach("foo.jpg", inline = True, cid = "foobar")
mail.html = f"<html><body><h1>Hey!</h1><p>This is the HTML content!<img src='cid:foobar'></body></html>"
```

If you wish to sign or encrypt mail using CMS (commonly known as S/MIME), you
need to set the security property of your email and configure it properly. For
example, for just signing, this works:

```python3
mail.security = mailcoil.CMS().sign(signer_keyfile = "my_key.pem", signer_certfile = "my_cert.pem", ca_certfile = "my_ca.pem")
```

If you additionally want to encrypt for three different targets, you can also
do:

```python3
mail.security.encrypt("target1.pem", "target2.pem", "target3.pem")
```

Similarly, you may also only encrypt without signing:

```python3
mail.security = mailcoil.CMS().encrypt("target.pem")
```

When your mail is finally set up, you can drop it off at the previously defined
dropoff:

```python3
dropoff.post(mail)
```

A complete example is therefore:

```python3
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

dropoff.post(mail)
```

## License
GNU GPL-3.
