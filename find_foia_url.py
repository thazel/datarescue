#!/usr/bin/env python
# encoding: utf-8
"""
find_foia_url.py

"""

import sys
import getopt
import requests
import string
import re


help_message = '''
The help message goes here.
'''

BASE_RECORD_URL = "https://foiaonline.regulations.gov/foia/action/public/view/record?objectId="
BASE_REQUEST_URL = "https://foiaonline.regulations.gov/foia/action/public/view/request?objectId="
BASE_OBJECT_ID = "090004d280"
SUFFIX_LENGTH = 6
SUCCESS_TEXT = "tracking\snumber"
EXPECTED_ERROR_TEXT = "DM_API_E_BADATTRNAME"
NON_PUBLIC_TEXT = "The\sspecified\sitem\sis\snot\spublicly\sviewable."
SLEEP_SECONDS = .1
DATA_DIR = "data"

class Usage(Exception):
	def __init__(self, msg):
		self.msg = msg


def main(argv=None):
	
	num_chars=2
	for char in range(num_chars)
	for letter in string.ascii_lowercase+string.digits:
	  processUrl("https://foiaonline.regulations.gov/foia/action/public/view/record?objectId=090004d280beaad"+letter)


def processUrl(url):
  r = requests.get(url).text
  if re.search(SUCCESS_TEXT,r,flags=re.IGNORECASE):
    print url
  elif re.search(NON_PUBLIC_TEXT,r,flags=re.IGNORECASE):
    print "NonPublic"
  elif re.search(EXPECTED_ERROR_TEXT,r,flags=re.IGNORECASE):
    f = 3
    #do nothing
  else:
    print r

if __name__ == "__main__":
	sys.exit(main())
