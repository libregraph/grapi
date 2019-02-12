# SPDX-License-Identifier: AGPL-3.0-or-later

import codecs
import email
import email.header
import imaplib
import os

HOST = 'email.kopano.com'
USER = os.getenv('GRAPI_USER')
PASSWORD = os.getenv('GRAPI_PASSWORD')

def login():
    M = imaplib.IMAP4_SSL(HOST)
    M.login(USER, PASSWORD)
    return M

def logoff(M):
    M.close()
    M.logout()

def convert_message(num, data):
    mail = email.message_from_bytes(data[0][1])
    name, addr = email.header.decode_header(mail['from'])
    name = codecs.decode(name[0], name[1] or 'utf-8').strip()
    addr = codecs.decode(addr[0], addr[1] or 'utf-8').strip()[1:-1]

    for part in mail.walk():
        if part.get_content_type() == 'text/plain':
            body = part.get_payload(decode=True)
            break

    return {
        'id': codecs.decode(num, 'utf-8'),
        'subject': mail['subject'],
        'from': {
            'emailAddress': {
                'name': name,
                'address': addr,
            }
        },
        'body': codecs.decode(body, 'utf-8'),
    }
