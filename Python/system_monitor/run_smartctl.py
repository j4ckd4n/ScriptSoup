import subprocess
import datetime
from datetime import datetime, timezone, timedelta
import time
import logging
import send_mail
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)

file_handler = logging.FileHandler('run_smartctl.log')
file_handler.setLevel(logging.DEBUG)

formatter = logging.Formatter('[%(asctime)s][%(levelname)s][%(threadName)s][run_smartctl.py]: %(message)s')
console_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)

logger.addHandler(console_handler)
logger.addHandler(file_handler)

SENDER = 'example1@example.com'
TO = 'toexample2@example.com'

def send_exception_mail(e, disk):
  subject = 'Error occurred while running smartctl tests on disk ' + disk
  html = "<code>" + str(e) + "</code>"
  send_mail.SendMessage(SENDER, TO, subject, html, str(e))

def get_smart_status(disk):
  cmd = 'smartctl -H /dev/' + disk
  try:
    status = subprocess.check_output(cmd, shell=True).decode('utf-8')
    logging.info('SMART status: ' + status)
    return status
  except Exception as e:
    logging.error('Failed to get SMART status: ' + str(e))
    send_exception_mail(e, disk)
    return None

def get_full_smart_info(disk):
  cmd = 'smartctl -x /dev/' + disk
  try:
    status = subprocess.check_output(cmd, shell=True).decode('utf-8')
    logging.info('Full SMART info: ' + status)
    return status
  except Exception as e:
    logging.error('Failed to get full SMART info: ' + str(e))
    send_exception_mail(e, disk)
    return None

def perform_test(disk, test_type):
  logging.info('Performing ' + test_type + ' test on disk ' + disk)
  try:
    cmd = 'smartctl -t ' + test_type + ' /dev/' + disk
    status = subprocess.check_output(cmd, shell=True).decode('utf-8')
    logging.info('Test started: ' + status)
  except Exception as e:
    logging.error('Failed to start test: ' + str(e))
    send_exception_mail(e, disk)
    return
  # Wait for the test to finish by parsing the data out of the output
  date = status.split('complete after ')[1].split(' UTC')[0]
  finish_date = datetime.strptime(date, '%a %b %d %H:%M:%S %Y').replace(tzinfo=timezone.utc) + timedelta(minutes=10)
  current_utc = datetime.now(timezone.utc).replace(tzinfo=timezone.utc)
  logging.info(f"Test should complete after {finish_date}. Current time: {current_utc}")
  while current_utc < finish_date:
    time.sleep(5)
    current_utc = datetime.now(timezone.utc).replace(tzinfo=timezone.utc)
  logging.info('Test finished. Checking status...')
  status = get_smart_status(disk)
  if status and 'PASSED' not in status:
    logging.error(test_type + ' test failed. Getting full status...')
    status = get_full_smart_info(disk)
    subject = 'Disk ' + disk + ' returned error state'
    html = "<code>" + status.replace('\n', '<br>') + "</code>"
    send_mail.SendMessage(SENDER, TO, subject, html, status)
  else:
    logging.info(test_type + ' test passed')
    subject = 'Disk ' + disk + ' is OK'
    html = "<code>" + status.replace('\n', '<br>') + "</code>"
    send_mail.SendMessage(SENDER, TO, subject, html, status)

def monitor_disks(disks, test_type):
  with ThreadPoolExecutor(max_workers=2, thread_name_prefix=f"Disk {test_type} scan") as executor:
    futures = {executor.submit(perform_test, disk, test_type): disk for disk in disks}
    for future in as_completed(futures):
      disk = futures[future]
      try:
        future.result()
      except Exception as e:
        logging.error(f"An error occurred while running tests on disk {disk}: {str(e)}")
        send_exception_mail(e, disk)

if __name__ == "__main__":
  parser = argparse.ArgumentParser(description='Run smartctl tests on disks')
  parser.add_argument("scan_type", help="Type of test to run (short or long)", type=str, choices=['short', 'long'])
  args = parser.parse_args()

  disks = ['sda', 'sdb']

  scan_type = args.scan_type

  monitor_disks(disks, scan_type)
