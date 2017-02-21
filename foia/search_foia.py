#!/usr/bin/env python
# encoding: utf-8
"""
search_foia.py

Queries the foiaonline.regulations.gov to retrieve (or attempt to, at least) all of the Freedom Of
Information Act requests stored in that system.

A rudimentary multi-threaded approach is used speed things up a little. Adding the
multi-threading makes the script somewhat brittle (pthread_cond_wait: Resource busy)
"""

import backoff
from bs4 import BeautifulSoup
import os
import Queue
import random
import re
import requests
import string
import sys
from threading import Thread
from threading import Lock
import time

"""Store data needed to make requests."""
class SearchRequest:
  def __init__(self):
    self.cookie_jar = None
    self.fp = None
    self.sourcePage = None
    
  def __str__(self):
    return "fp: " + self.fp + "    sourcePage: " + self.sourcePage
    
  def setCookieJar(self, cookie_jar):
    self.cookie_jar = cookie_jar
    
  def setRequestParams(self, fp, sourcePage):
    self.fp = fp
    self.sourcePage = sourcePage

"""Store current state of the search."""
class SearchState:
  def __init__(self, processed_objects):
    self.total_processed = 0
    self.total_skipped = 0
    self.processed_objects = processed_objects
    
  def getProcessedObjects(self):
    return self.processed_objects
  
  def getTotalProcessed(self):
    return self.total_processed
  
  def incrementTotalProcessed(self):
    self.total_processed += 1
    
  def getTotalSkipped(self):
    return self.total_skipped
  
  def incrementTotalSkipped(self):
    self.total_skipped += 1
    
"""Does all the work."""
class FoiaSearchRunner:

  def __init__(self):
    self.search_url_template =  (
        'https://foiaonline.regulations.gov/foia/action/public/search/runSearch?'
        '&__fp={}&_sourcePage={}&searchParams.searchTerm={}&pageSize={}&d-5509183-p={}'
        '&searchParams.forAppeal=true&searchParams.allAgencies=true&searchParams.forReferral=true&event=runSearch'
        '&searchParams.forRequest=true'
        '&searchParams.forRecord=true#resultsPerPage')
    self.cookie_url = 'https://foiaonline.regulations.gov/foia/action/public/search'
    self.result_file_path = 'results/foia_full.txt'
    self.error_file_path = 'results/error_url.txt'
    self.html_parser = 'lxml'#'html5lib'
    self.total_processed = 0
    self.total_skipped = 0
    self.page_size = 1000
    self.num_threads = 1
    self.request_context = None
    self.processed_objects = self.load_previous_results(self.result_file_path)
    self.search_state = SearchState(self.processed_objects)
    self.output_file = open(self.result_file_path, 'a')
    self.error_file = open(self.error_file_path, 'a')

  def run(self):
    # trouble letters: ['i', 'j', 'l', 'm']
    for letter in string.ascii_lowercase:
      # get cookies each time
      self.request_context = self.loadRequestContext()
      
      total_results = self.loadResultCount(letter)
      print "Processing letter " + letter + ". " + str(total_results) + " results, time: " + str(time.time())
      
      if total_results <= 0:
        continue

      num_pages = (total_results // self.page_size) + 2
      url_queue = Queue.Queue()

      for i in range(1, num_pages):
        search_url = self.search_url_template.format(
            self.request_context.fp, self.request_context.sourcePage, 
            letter, str(self.page_size), str(i))
        url_queue.put(search_url)
      
      # new lock created for each letter
      lock = Lock()
      
      # this would better be done via async HTTP requests, but as a first pass this is OK.
      
      if self.num_threads == 1:
        self.process_url(url_queue, lock, self.output_file, self.error_file, self.search_state)
      else:
        for t in range(self.num_threads):
          t = Thread(
              target = self.process_url, 
              args=(url_queue, lock, self.output_file, self.error_file, self.search_state))
          t.start()
        url_queue.join()

      print "Processing complete. Set size: {}, Time: {}\n".format(sys.getsizeof(processed_objects),  str(time.time()))
      output_file.flush()

    output_file.close()
    error_file.close()
    
  def loadRequestContext(self):
    cookie_response = self.make_request(self.cookie_url, None)
    return self.parseSetup(cookie_response)
  
  def parseSetup(self, response):
    search_request = SearchRequest()
    search_request.setCookieJar(requests.cookies.RequestsCookieJar())
    soup = BeautifulSoup(response.text, self.html_parser)
    fp_tag = soup.find('input', attrs={"type": "hidden", "name":"__fp"})
    source_tag = soup.find('input', attrs={"type": "hidden", "name":"_sourcePage"})
    search_request.setRequestParams(fp_tag["value"], source_tag["value"])
    return search_request
    
  def loadResultCount(self, current_letter):
    search_url = self.search_url_template.format(
        self.request_context.fp, self.request_context.sourcePage,
        current_letter, "1", "1")
    search_result = self.make_request(search_url, self.request_context.cookie_jar)
    num_results_soup = BeautifulSoup(search_result.text, self.html_parser)

    return self.parseNumResults(num_results_soup)

  def parseNumResults(self, search_soup):
    num_results_tag = search_soup.find("div", text=re.compile("items")).string.replace(",", "")
    num_results_string = re.search("([0-9]+)", num_results_tag)
    return int(num_results_string.group(0))

  @backoff.on_exception(backoff.expo,
                        requests.exceptions.RequestException,
                        max_tries=8)
  def make_request(self, url, cookie_jar):
    return requests.get(url, cookies=cookie_jar)


  def process_url(self, url_queue, lock, output_file, error_file, search_state):
    while not url_queue.empty():
      time.sleep(random.random())
      url = url_queue.get()
      search_result = self.make_request(url, self.request_context.cookie_jar)
      self.parse_result(search_result, output_file, error_file, search_state, url, lock)
      url_queue.task_done()

  def parse_result(self, result_text, output_file, error_file, search_state, url, lock):
    processed_objects = search_state.getProcessedObjects()
    try:
      search_soup = BeautifulSoup(result_text.text, self.html_parser)
    except:
      print "Error for URL: {}".format(url)
      with lock:
        error_file.write(url)
        return
    
    for t in search_soup.select('a[href^="/foia/action/public/view/"]'):
      object_id = re.search("objectId=([0-9a-z]+)", t["href"]).groups(1)
      if object_id not in processed_objects:
        url = re.sub(";jsessionid=[0-9A-Z]+", "", t["href"])
        url = url.replace("&fromSearch=true", "")
        with lock:
          processed_objects.add(object_id)
          search_state.incrementTotalProcessed()
          output_file.write(url+"\n")
      else:
        with lock:
          search_state.incrementTotalSkipped()
      if (search_state.getTotalProcessed() + search_state.getTotalSkipped()) % 10000 == 0:
        print "Processed: {} Skipped: {} Set size : {} Time: {}".format(search_state.getTotalProcessed(), search_state.getTotalSkipped(), sys.getsizeof(search_state.getProcessedObjects()), str(time.time()))
    return search_state


  def load_previous_results(self, file_path):
    result_file = open(file_path, 'r')
    processed_objects = set()
    for line in result_file:
      object_id = re.search("objectId=([0-9a-z]+)", line).groups(1)
      processed_objects.add(object_id)
    print "Loaded {} results.".format(str(len(processed_objects)))
    result_file.close()
    return processed_objects
    
if __name__ == '__main__':
  FoiaSearchRunner().run()
