#!/usr/bin/python3
# SPDX-License-Identifier: AGPL-3.0-or-later


import argparse
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate
from io import BytesIO

import kopano
from PIL import Image


def formatemail(user):
    return "{fullname} <{email}>".format(fullname=user.fullname, email=user.email)


def get_internal_plaintext(user, sender):
    msg = MIMEMultipart('alternative')
    msg['Date'] = formatdate(localtime=True)
    msg['Subject'] = 'Test company plain text email'
    msg['From'] = formatemail(sender)
    msg['To'] = formatemail(user)
    msg.attach(MIMEText("This is a simple plaintext body"))

    return msg


def get_plaintext(user):
    msg = MIMEMultipart('alternative')
    msg['Date'] = formatdate(localtime=True)
    msg['Subject'] = 'Test external plain text email'
    msg['From'] = 'John Doe <j.doe@example.com>'
    msg['To'] = formatemail(user)
    msg.attach(MIMEText("This is a simple plaintext body"))

    return msg


def get_cc_mail(user):
    msg = MIMEMultipart('alternative')
    msg['Date'] = formatdate(localtime=True)
    msg['Subject'] = 'Test CC email'
    msg['From'] = 'John Doe <j.doe@example.com>'
    msg['To'] = formatemail(user)
    msg['Cc'] = "{}, {}".format(formatemail(user), 'Jane Doe <j.doe@example.com>')
    msg.attach(MIMEText("This is a simple multipart plaintext/html mail"))
    msg.attach(MIMEText("<html><body><p>This is a multipart email</p></body></html>", "html"))

    return msg


def get_bcc_mail(user):
    msg = MIMEMultipart('alternative')
    msg['Date'] = formatdate(localtime=True)
    msg['Subject'] = 'Test BCC email'
    msg['From'] = 'John Doe <j.doe@example.com>'
    msg['To'] = formatemail(user)
    msg['Bcc'] = "{}, {}".format(formatemail(user), 'Jane Doe <j.doe@example.com>')
    msg.attach(MIMEText("This is a simple multipart plaintext/html mail"))
    msg.attach(MIMEText("<html><body><p>This is a multipart email</p></body></html>", "html"))

    return msg


def get_multipart(user):
    msg = MIMEMultipart('alternative')
    msg['Date'] = formatdate(localtime=True)
    msg['Subject'] = 'Test multipart email'
    msg['From'] = 'John Doe <j.doe@example.com>'
    msg['To'] = formatemail(user)
    msg.attach(MIMEText("This is a simple multipart plaintext/html mail"))
    msg.attach(MIMEText("<html><body><p>This is a multipart email</p></body></html>", "html"))

    return msg


def get_attachment_mail(user):
    msg = MIMEMultipart('related')
    msg['Date'] = formatdate(localtime=True)
    msg['Subject'] = 'Test attachment email'
    msg['From'] = 'John Doe <j.doe@example.com>'
    msg['To'] = formatemail(user)
    msgAlt = MIMEMultipart('alternative')
    msg.attach(msgAlt)
    msgAlt.attach(MIMEText("This is a simple multipart plaintext/html mail"))
    msgAlt.attach(MIMEText("<html><body><p>This is an email with attachment</p></body></html>", "html"))

    with BytesIO() as buf:
        img = Image.new('RGB', (60, 30), color='red')
        img.save(buf, 'JPEG')

        part = MIMEImage(buf.getvalue(), "test.jpg")
        part.add_header("Content-Disposition", "attachment; filename=test.jpg")
        msg.attach(part)

    return msg


def get_inline_image_mail(user):
    msg = MIMEMultipart('related')
    msg['Date'] = formatdate(localtime=True)
    msg['Subject'] = 'Test inline image html'
    msg['From'] = 'John Doe <j.doe@example.com>'
    msg['To'] = formatemail(user)
    msgAlt = MIMEMultipart('alternative')
    msg.attach(msgAlt)
    msgAlt.attach(MIMEText("This is a simple multipart plaintext/html mail"))
    msgAlt.attach(MIMEText('<html><body><p>This is an inline image email</p><img src="cid:image1"></body></html>', "html"))

    with BytesIO() as buf:
        img = Image.new('RGB', (60, 30), color='red')
        img.save(buf, 'JPEG')

        part = MIMEImage(buf.getvalue(), "test.jpg")
        part.add_header('Content-ID', '<image1>')
        msg.attach(part)

    return msg


def get_external_image(user):
    msg = MIMEMultipart('alternative')
    msg['Date'] = formatdate(localtime=True)
    msg['Subject'] = 'Test external image'
    msg['From'] = 'John Doe <j.doe@example.com>'
    msg['To'] = formatemail(user)
    msg.attach(MIMEText("This is a simple multipart plaintext/html mail"))
    img_url = 'https://webapp.kopano.com/signin/v1/static/media/loginscreen-bg.80ed0be9.jpg'
    msg.attach(MIMEText('<html><body><p>This is an email with external image</p><img src="{}"></body></html>'.format(img_url), "html"))

    return msg


def get_important_mail(user):
    msg = MIMEMultipart('alternative')
    msg['Date'] = formatdate(localtime=True)
    msg['Subject'] = 'Test high importance plain text email'
    msg['From'] = 'John Doe <j.doe@example.com>'
    msg['X-Priority'] = "2"
    msg['To'] = formatemail(user)
    msg.attach(MIMEText("This is a simple plaintext body"))

    return msg


def main(user, sender, nuke=False, count=0):
    # Nuke inbox entries if set
    if nuke:
        user.inbox.empty()

    if count:
        msg = get_plaintext(user)
        eml = msg.as_bytes()
        print('creating {} plaintext emails'.format(count))

        for _ in range(0, count):
            user.inbox.create_item(eml=eml)

        return

    # Normal test data

    msg = get_internal_plaintext(user, sender)
    user.inbox.create_item(eml=msg.as_bytes())

    msg = get_plaintext(user)
    user.inbox.create_item(eml=msg.as_bytes())

    msg = get_multipart(user)
    user.inbox.create_item(eml=msg.as_bytes())

    msg = get_cc_mail(user)
    user.inbox.create_item(eml=msg.as_bytes())

    msg = get_bcc_mail(user)
    user.inbox.create_item(eml=msg.as_bytes())

    msg = get_attachment_mail(user)
    user.inbox.create_item(eml=msg.as_bytes())

    msg = get_important_mail(user)
    user.inbox.create_item(eml=msg.as_bytes())

    msg = get_inline_image_mail(user)
    user.inbox.create_item(eml=msg.as_bytes())

    msg = get_external_image(user)
    user.inbox.create_item(eml=msg.as_bytes())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Create test emails in the specified users inbox')
    parser.add_argument('--user', type=str, help='The user to import emails (kopano user)', required=True)
    parser.add_argument('--sender', type=str, help='The Kopano user sender', required=True)
    parser.add_argument('--count', type=int, help='Create given amount of emails (for performance testing)', default=0)
    parser.add_argument('--nuke-inbox', dest='nuke', help='If set, all mail items from the users inbox will be removed', action='store_true', default=False)
    args = parser.parse_args()

    server = kopano.server()
    user = server.user(args.user)
    sender = server.user(args.sender)

    main(user, sender, nuke=args.nuke, count=args.count)
