#!/usr/bin/env python3

# Copyright 2021-2022 Board of Trustees, University of Illinois
# Permission to use, copy, modify, and/or distribute this software for any purpose with or without fee is hereby granted, provided that the above copyright notice and this permission notice appear in all copies.

# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

# This code was formatted with python3 -m black CanvasCalendar.py

import os
import sys
import re
import datetime
from datetime import timezone, timedelta

from dateutil import tz
from dateutil.parser import parse, parserinfo

# f-strings require python 3.6+
assert sys.version_info >= (3, 6)

try:
    import requests
except Exception:
    print(
        "Please install the requests library e.g. Using pip or pip3, \npip install requests"
    )
    sys.exit(1)

# This python3 script requires the requests library, which can usually be installed with
# pip3 install requests

# Canvas documentation-
# https://canvas.instructure.com/doc/api/calendar_events.html
# https://canvas.instructure.com/doc/api/file.pagination.html
# Note the phrase, 'They will be absolute urls that include all parameters necessary to retrieve the desired current, next, previous, first, or last page'... is false

# Python request library documentation
# https://docs.python-requests.org/en/latest/
#


def about():
    about = """\
Automatic Canvas Calendar Event Creator

Copyright 2021 Board of Trustees, University of Illinois

Permission to use, copy, modify, and/or distribute this software for any purpose with or without fee is hereby granted, provided that the above copyright notice and this permission notice appear in all copies.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

Acknowledgements:
Supported by a University of Illinois Grainger College of Engineering SIIP Grant 2021
Original version by L Angrave 2021.
Thanks to David Dalpiaz, the SIIP team and Illinois for testing and contributions.

Usage: python3 SCRIPTNAME <courseid> [listingfile]

Courseid is a small integer.

The script experts CANVAS_ACCESS_TOKEN environment variable to be set.
To create your Canvas Access Token, login to https://canvas.illinois.edu/
Left hand bar select Account then Settings. Scroll down to Approved Integrations and click New Access Token

Without a listing file script will list all events in the given course and exit

With a listing file the script will create new events. Events previously created in the course by this script will be first be deleted. An example event list file is below-

# Blank lines and lines starting with a hash character are ignored
# Dates should be in ISO 8601 format, "%Y-%m-%dT%H:%M:%SZ"
# A small set of timezone are supported-
# "Z" ( Zulu/GMT ) "CST" (-6) "CDT" (-5) 
# and "CT" (-5 or -6 depending on date)

# start-time end-time title description (each field separated by a tab character)

2021-09-20T11:00:00CT	2021-09-20T12:00:00CT	MP2-Hello	<p>ABC</p>
2021-09-23T11:00:00CDT	2021-09-23T12:00:00CDT	MP3-World	https://www.illinois.edu
2021-09-25T11:00:00CST	2021-09-23T12:00:00CST	MP4-ABCDE	https://www.cs.illinois.edu

"""  # Please add your name to the above if you've improved this code.
    print(about.replace("SCRIPTNAME", sys.argv[0]))


def truncate(s, maxlen=20):
    return s if len(s) < maxlen else s[: maxlen - 1] + "…"


# Canvas silently removes some html content in the description such as html comment <-- -->
# The following hidden text is added to the description and later allows us to check which events we can automatically delete before creating new events

MY_EVENT_TAG = '<p style="display: none;">External Event Details</p>'


def getCanvasBaseUrl():
    return os.environ.get("CANVAS_BASE_URL", "https://canvas.illinois.edu")


def create_event(session, course_id, event):
    url1 = f"{ getCanvasBaseUrl() }/api/v1/calendar_events"

    data1 = {
        "calendar_event[context_code]": f"course_{course_id}",
        "calendar_event[start_at]": event["start_at"],
        "calendar_event[end_at]": event["end_at"],
        "calendar_event[title]": event["title"],
        "calendar_event[description]": event["description"] + MY_EVENT_TAG,
    }

    with session.post(url1, data=data1) as r:
        if r.ok:
            return
        print(r.headers["status"], r.text)
    raise Exception("Could not create event")


def get_all_events(session, course_id):
    url1 = f"{ getCanvasBaseUrl() }/api/v1/calendar_events/"
    data1 = {
        "context_codes[]": f"course_{course_id}",
        "all_events": "true",
        "per_page": "100",
    }

    all_events = []
    page_count = 0
    max_page_count = 30
    while page_count < max_page_count:
        # https://docs.python-requests.org/en/latest/user/advanced/#link-headers
        with session.get(url1, data=data1) as r:
            if not r.ok:
                print(r.headers["status"], r.text)
                raise Exception()
            events = r.json()
            all_events.extend(events)
            print(f"Found {len(all_events)} existing event(s)")
            page_count += 1
            if ("next" not in r.links) or len(events) == 0:
                break
            else:
                url1 = r.links["next"]["url"]
    if page_count == max_page_count:
        print(f"Reached page limit on event results. Found {len(all_events)} in {page_count} pages.")

    return all_events


def delete_one_event(session, id):
    url1 = f"{getCanvasBaseUrl()}/api/v1/calendar_events/{id}"
    with session.delete(url1) as r:
        if not r.ok:
            print(f"Could not delete event id {id}:{r.headers['status']}:{r.text}")


def delete_my_old_events(session, course_id):
    all_events = get_all_events(session, course_id)
    # e['description'] can be None
    my_events = [
        e
        for e in all_events
        if e["description"] and e["description"].endswith(MY_EVENT_TAG)
    ]

    if len(my_events) == 0:
        print("No previous events to remove")
        return

    print(
        f"Removing {len(my_events)} event(s) previously created with this script",
        end="",
        flush=True,
    )
    for e in my_events:
        print(".", end="", flush=True)
        delete_one_event(session, e["id"])
    print()


def parse_date_format(name, index, value):
    ISO8601 = "%Y-%m-%dT%H:%M:%SZ"
    tzinfos = {x: tz.tzutc() for x in parserinfo().UTCZONE}

    tzinfos["CST"] = timezone(timedelta(hours=-6))  # Central Standard Time definition
    tzinfos["CDT"] = timezone(timedelta(hours=-5))  # Central Daylight Time definition
    tzinfos["CT"] = tz.gettz("America/Chicago")

    try:
        d = parse(value, tzinfos=tzinfos)
        if d.tzinfo is None:
            raise ValueError("No Timezone")
        d = d.astimezone(tz.tzutc())

        return d.strftime(ISO8601)
    except ValueError:
        print(
            f"{name} at line {index+1}: {value} expected date/time ISO8601 format like 2021-09-20T06:00:00Z or similar e.g. 2021-09-20T11:00:00 CT"
        )
    raise Exception(f"Invalidate date at line {index+1}")


def wrap_description(d):
    result = d
    if d.startswith("http"):

        # Dont use quote() etc; we need to preserve ":" in the "http:"
        d = d.replace('"', "%22")
        result = f"""<p><a class="inline_disabled" href="{d}" target="_blank" rel="noopener">Open in new window</a></p>"""
    return result


def read_event_file(filename):
    delimiter = "\t"
    new_events = []
    with open(filename) as file:
        for index, line in enumerate(file):
            line = line.rstrip()
            if len(line) == 0 or line[0] == "#":
                continue

            start_at, end_at, title, raw_description = line.split(delimiter)

            description = wrap_description(raw_description)

            start_at = parse_date_format(
                "start_at", index, start_at
            )  # e.g. 2021-09-20T11:00:00Z
            end_at = parse_date_format("end_at", index, end_at)
            # print(f"end_at = {end_at}")

            new_events.append(
                {
                    "start_at": start_at,
                    "end_at": end_at,
                    "title": title,
                    "description": description,
                }
            )
    return new_events


def print_all_events(session, course_id):
    for e in get_all_events(session, course_id):
        print(f"{e['title']}: {e['description']}")


def main():
    if len(sys.argv) <= 1:
        return about()

    event_file = None
    try:
        course_id = int(sys.argv[1])  #'655'
        if len(sys.argv) > 2:
            event_file = sys.argv[2]  #'events.list'

    except Exception as e:
        print(e)
        about()
        sys.exit(1)

    canvas_access_token = os.environ.get("CANVAS_ACCESS_TOKEN", None)
    if canvas_access_token is None:
        instructions = """\     
CANVAS_ACCESS_TOKEN environment variable was not set.

To create your Canvas Access Token, login to your Canvas website e.g. https://canvas.illinois.edu/
Use the left area and select Account then Settings. Scroll down to Approved Integrations and click New Access Token

Linux Tip: Create a file canvastoken.sh,
export CANVAS_ACCESS_TOKEN='<Your token>'
Then use "source canvastoken.sh" to set the environment variable in your shell environment
"""
        print(instructions)

        canvas_access_token = input("Your Canvas Authorization Key?")

    session = requests.Session()
    session.headers.update({"Authorization": f"Bearer {canvas_access_token}"})

    # Check we can parse the file before changin' things.

    if event_file:
        new_events = read_event_file(event_file)
        delete_my_old_events(session, course_id)

        print(f"Creating {len(new_events)} new event(s).")
        for index, event in enumerate(new_events):
            print(
                f"{index+1}/{len(new_events)}. {truncate( event['title'] + ' ' + event['description'],80)}"
            )
            create_event(session, course_id, event)
        return

    print_all_events(session, course_id)
    return


if __name__ == "__main__":
    # execute only if run as a script
    main()
