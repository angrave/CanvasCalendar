import os
import sys
#import json
import requests
import urllib3
from urllib.parse import quote

#import re
from datetime import datetime

#see
# https://canvas.instructure.com/doc/api/calendar_events.html
# pip3 install requests

def truncate(s, maxlen = 20):
    return s if len(s) <  maxlen else s[:maxlen-1] + "…"

MY_EVENT_TAG = '<!--canautoupdate-->'   
 
def create_event(session,course_id,event):
    url1 = f"{CANVAS_BASE_URL}/api/v1/calendar_events"
    
    data1 = {
        'calendar_event[context_code]': f"course_{course_id}",
        'calendar_event[start_at]': event['start_at'], 
        'calendar_event[end_at]': event['end_at'], 
        'calendar_event[title]': event['title'], 
        'calendar_event[description]': event['description'] + MY_EVENT_TAG}
        
    print(f"{truncate(event['title'],15)},{truncate(event['description'],15)}")
    result=session.post(url1,data = data1)
    print(result.text)
    
    #url2 = CANVAS_BASE_URL+f"/api/v1/calendar_events/{code}"
    #data2 = {'events[description]': description}
    #session.put(url1,data = data2)

def delete_old_events(session,course_id):   
    # Get all events and remove the ones with "!<--autodelete->" in the description
    url1 = CANVAS_BASE_URL+f"/api/v1/calendar_events/"
    data1 = {
        'calendar_event[context_code]': f"course_{course_id}"
        }
    result= session.post(url1, data = data1).json()
    print(result)
    #session.delete(url)
    pass


def delete_one_event(session,id):
    url1=f"{CANVAS_BASE_URL}/api/v1/calendar_events/{id}"
    result=session.delete(url1)

def about():
    about = '''\
Automatic Canvas Calendar Event Creator

Copyright 2021 Board of Trustees, University of Illinois

Permission to use, copy, modify, and/or distribute this software for any purpose with or without fee is hereby granted, provided that the above copyright notice and this permission notice appear in all copies.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

Acknowledgements:
Supported by a U ofI Grainger College of Engineering SIIP Grant 2021
Original version by L Angrave. Thanks to (your names here?) for improving it!

Usage: python3 setcalendar.py <courseid> <listingfile>
''' # Please add your name to the above if you've improved this code.
    print(about)
    
    

CANVAS_BASE_URL = os.environ.get('CANVAS_BASE_URL','https://canvas.illinois.edu')

def date_format_check(name,index,value):
    try: # ISO 8601 format
        datetime.strptime(value,"%Y-%m-%dT%H:%M:%SZ")
        return value
    except ValueError:
        pass
    print(f"{name} at line {index+1}: {value} expected date/time format like 2021-09-20T11:00:00Z")
    raise Exception(f"Invalidate date at line {index+1}")

def wrap_description(d):
    result = d
    if d.startswith('http'):
        result = f"<a src={quote(d)} target=_blank>details</a>"  
    return result + MY_EVENT_TAG
      
def main():

    CANVAS_ACCESS_TOKEN = os.environ.get('CANVAS_ACCESS_TOKEN',None)
    if CANVAS_ACCESS_TOKEN is None:
        print("CANVAS_ACCESS_TOKEN environment was not set")
        CANVAS_ACCESS_TOKEN = input("Your Canvas Authorization Key?")
    
    
    try:
        course_id = int(sys.argv[1]) #'655'
        DELIM = '\t'     
        EVENT_FILE = sys.argv[2] #'events.list'
        
    except Exception as e:
        print(e)
        about()
        sys.exit(1)
            
    # Check we can parse the file before changin' things.
    new_events = []
    
    with open(EVENT_FILE) as file:
        for index, line in enumerate(file):
            
            line = line.rstrip()
            if(len(line) == 0 or line[0] == '#'):
                continue
            
            start_at,end_at,title,rawdescription = line.split(DELIM)
            
            description = wrap_description(rawdescription)
            print(description)
            date_format_check('start_at',index,start_at) # e.g. 2021-09-20T11:00:00Z
            date_format_check('end_at',index, end_at) 
            new_events.append( {'start_at':start_at, 'end_at':end_at, 'title':title, 'description':description})

    session = requests.Session()
    session.headers.update({'Authorization':  "Bearer "+ CANVAS_ACCESS_TOKEN})

    delete_old_events(session,course_id)
    
    print(f"Creating {len(new_events)} new events")
    for event in new_events:
       create_event(session,course_id,event)

main()
