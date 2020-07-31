#!/usr/bin/python
# SPDX-License-Identifier: AGPL-3.0-or-later

import argparse
import os
import sys
from datetime import datetime, timedelta

import kopano
import requests

EVENT = {
    'showAs': 'busy',
    'subject': 'test script meeting request',
}


MODIFICATIONS = ['remove_attendee', 'add_attendee', 'change_subject', 'change_time', 'delete']


def format_datetime(dtime):
    fmt = '%Y-%m-%dT%H:%M:%S'
    return {
        'timeZone': 'UTC',
        'dateTime': dtime.strftime(fmt)
    }


def format_emailaddress(user):
    return {
        'type': 'required',
        'emailAddress': {
            'name': user.fullname,
            'address': user.email
        }
    }


def format_attendees(attendees):
    return [format_emailaddress(attendee) for attendee in attendees]


def create_meetingrequest(api_url, token, organizer, attendee, start):
    fmt = '%H:%M'
    event = EVENT
    end = start + timedelta(hours=1)

    event['subject'] = '{} {}'.format(event['subject'], start.strftime(fmt))
    event['attendees'] = format_attendees([attendee])
    event['start'] = format_datetime(start)
    event['end'] = format_datetime(end)
    event['organizer'] = format_emailaddress(organizer)

    headers = {
        'Authorization': 'Bearer {}'.format(token),
        'Content-Type': 'application/json'
    }

    response = requests.post('{}/api/gc/v1/me/events'.format(api_url), headers=headers, json=event)
    if response.status_code == 403:
        print('Access token expired', file=sys.stderr)
        sys.exit(1)

    return response.json()


def modify_meetingrequest(api_url, token, basedate, modification, event, modify_attendee):
    update = {}
    headers = {
        'Authorization': 'Bearer {}'.format(token),
        'Content-Type': 'application/json'
    }
    url = '{}/api/gc/v1/me/events/{}'.format(api_url, event['id'])

    if modification == 'change_time':
        start = basedate + timedelta(hours=1)
        end = start + timedelta(hours=1)
        update['start'] = format_datetime(start)
        update['end'] = format_datetime(end)
    elif modification == 'change_subject':
        update['subject'] = 'meeting request updated subject'
    elif modification == 'add_attendee':
        # TODO: this appends original users due to a grapi bug
        attendees = event['attendees']
        attendees.append(format_emailaddress(modify_attendee))
        update['attendees'] = attendees
    elif modification == 'remove_attendee':
        # TODO: this does not remove original users due to a grapi bug
        attendees = [attendee for attendee in event['attendees'] if attendee['emailAddress']['address'] != modify_attendee.email]
        update['attendees'] = attendees

    if modification != 'delete':
        response = requests.patch(url, headers=headers, json=update)
    elif modification == 'delete':
        response = requests.delete(url, headers=headers)

    if response.status_code == 403:
        print('Access token expired', file=sys.stderr)
        sys.exit(1)

    if modification == 'delete':
        print('Delete meeting, should sent cancellation')
    else:
        print('Updated meeting request with change: {}'.format(update))


if __name__ == "__main__":
    basedate = datetime.utcnow()+timedelta(days=1)

    parser = argparse.ArgumentParser(description='Test creating and updating meeting requests')
    parser.add_argument('--organizer', type=str, help='The username of the organizer', required=True)
    parser.add_argument('--attendee', type=str, help='The username of the attendee', required=True)
    parser.add_argument('--modify-attendee', type=str, help='The username of the attendee to add/remove for add_attendee/remove_attendee')
    parser.add_argument('--token', type=str, help='The bearer token value', default=os.getenv('TOKEN_VALUE', ''))
    parser.add_argument('--api', type=str, help='The API url', default=os.getenv('KC_API', ''))
    parser.add_argument('--basedate', type=str, help='The base date for the calendar default({})'.format(basedate),
                        default=basedate)
    parser.add_argument('--meeting-update', type=str, help='The meeting update modification', choices=MODIFICATIONS)

    args = parser.parse_args()
    if not args.modify_attendee and args.meeting_update in ['add_attendee', 'remove_attendee']:
        print('Missing --modify-attendee for adding/removing an attendee', file=sys.stderr)
        sys.exit(1)

    server = kopano.server()
    organizer = server.user(args.organizer)
    attendee = server.user(args.attendee)

    event = create_meetingrequest(args.api, args.token, organizer, attendee, args.basedate)

    print('Created meeting request with entryid: {}'.format(event['id']))

    if args.meeting_update:
        modify_attendee = server.user(args.modify_attendee) if args.modify_attendee else None
        modify_meetingrequest(args.api, args.token, args.basedate, args.meeting_update, event, modify_attendee)
