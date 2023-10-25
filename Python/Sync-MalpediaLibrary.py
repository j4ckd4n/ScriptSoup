import sqlite3
import os
import requests
import requests_cache
import logging
import time
import webbrowser
import sys

from threading import Thread
from datetime import datetime
from pybtex.database import parse_bytes
from pybtex.database import BibliographyData

from windows_toasts import InteractableWindowsToaster, ToastText4, ToastButton, ToastActivatedEventArgs, ToastDismissedEventArgs, ToastDismissalReason

initial = sys.argv[1] if len(sys.argv) > 1 else ""

class Toaster(Thread):
  def __init__(self, headline, first_line, second_line):
    super().__init__(name=first_line)
    self._headline = headline
    self._first_line = first_line
    self._second_line = second_line
    
    self._can_exit = False

  def btn_callback(self, event_args: ToastActivatedEventArgs):
    if event_args.arguments.startswith("openurl="):
      url = event_args.arguments.split("=")[1]
      logging.info(f"opening url: {url}")
      webbrowser.open(url, 2)
      self._can_exit = True

  def dismised_callbasck(self, event_args: ToastDismissedEventArgs):
    if event_args.reason == ToastDismissalReason.USER_CANCELED:
      logging.debug(f"user dismissed: {self._first_line}")
      self._can_exit = True

  def run(self):
    windows_toast = InteractableWindowsToaster("Malpedia Sync")
    toast = ToastText4()
    toast.SetHeadline(self._headline)
    toast.SetFirstLine(self._first_line)
    toast.SetSecondLine(self._second_line)
    toast.AddAction(ToastButton("Open Article", f"openurl={url}"))
    toast.on_activated = self.btn_callback
    toast.on_dismissed = self.dismised_callbasck
    windows_toast.show_toast(toast)
    while not self._can_exit:
      time.sleep(1) # make sure we don't overload the OS
      continue

requests_cache.install_cache("malpedia_cache", expire_after=7200)

current_dt = datetime.fromtimestamp(time.time())
log_name = current_dt.strftime("%Y-%m-%d")

temp_dir = os.getenv("TMP")

# logger config
logFormatter = logging.Formatter("%(asctime)s %(levelname)s:%(message)s")
logging.basicConfig(filename=f"{temp_dir}\\sync_malpedialibrary_{log_name}_log.txt", level=logging.DEBUG, format=logFormatter._fmt)
consoleHandler = logging.StreamHandler(sys.stdout)
consoleHandler.setFormatter(logFormatter)
logging.getLogger().addHandler(consoleHandler)
#

windows_toaster = InteractableWindowsToaster("Malpedia Sync")

malpedia_url = "https://malpedia.caad.fkie.fraunhofer.de/library/download"

home_folder = os.getenv("USERPROFILE")
db_folder_path = f"{home_folder}\\Documents\\Databases"

db_path = f"{db_folder_path}\\malpedia.db"

if not os.path.exists(db_folder_path):
  logging.info("db_folder_path directory made")
  os.makedirs(db_folder_path)

logging.info(f"performing request to {malpedia_url} ")
res = requests.get(malpedia_url)
logging.info(f"Request from cache: {res.from_cache}")
content = res.content
logging.info("parsing received data...")
parsed_bib: BibliographyData = parse_bytes(content, "bibtex")

logging.info(f"loading database from {db_path}")
sql = sqlite3.connect(db_path)
cursor = sql.cursor()

logging.info("creating the database table if it does not exist.")
cursor.execute("CREATE TABLE IF NOT EXISTS malpedia_table (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, date TEXT, org TEXT, url TEXT, url_date TEXT);")

# # check if anything exists in the database.
# # make sure that the difference between the recent pull and the cached db is not more than 20 items otherwise system DoS may occur due to toast creation.
# cursor.execute("SELECT COUNT(*) FROM malpedia_table;")
# count = cursor.fetchone()[0]
# difference = len(parsed_bib.entries.items()) - count
# if difference > 20:
#   logging.warning(f"there are {difference} more items in the new pull than cached db, to prevent DoS, not displaying toasts...")
#   initial = "initial"

threads = []
for key, item in parsed_bib.entries.items():
  title = item.fields['title'].strip("{}")

  cursor.execute("SELECT id, title FROM malpedia_table WHERE title=?;", (title,))
  sql_res = cursor.fetchone()

  if sql_res == None:
    date = item.fields['date']
    org = None
    if 'organization' in item.fields:
      org = item.fields['organization']
    url = item.fields['url'].strip("{}")
    url_date = item.fields['urldate']

    if "initial" not in initial:
      logging.debug(f"creating new thead for: {title}")
      thread = Toaster("New Malpedia Article", f"{title}", f"{url}")
      thread.start()
      threads.append(thread)

    cursor.execute("INSERT INTO malpedia_table VALUES(?, ?, ?, ?, ?, ?);", (None, title, date, org, url, url_date))
    logging.info(f"new entry added: {title}")

logging.info("committing sql changes to db")
sql.commit()
logging.info('closing database')
cursor.close()
sql.close()

content = None
parsed_bib = None

for thread in threads:
  logging.info(f"attempting to join thread: {thread.name}")
  thread.join()