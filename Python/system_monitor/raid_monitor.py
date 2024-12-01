import subprocess
import send_mail
import logging

# --- Logging configuration ---
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)

file_handler = logging.FileHandler('raid_monitor.log')
file_handler.setLevel(logging.DEBUG)

formatter = logging.Formatter('[%(asctime)s][%(levelname)s][%(threadName)s][RaidMonitor]: %(message)s')
console_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)

logger.addHandler(console_handler)
logger.addHandler(file_handler)

# --- Configuration ---
RAID_DEV = '/dev/md0'
SENDER = '<email>'
TO = '<email>@'

# --- Functions ---
def send_exception_mail(e):
  subject = 'RAID error occurred on ' + RAID_DEV
  html = "<code>" + str(e) + "</code>"
  send_mail.SendMessage(SENDER, TO, subject, html, str(e))

def get_raid_status():
  cmd = 'mdadm --detail ' + RAID_DEV
  try:
    status = subprocess.check_output(cmd, shell=True).decode('utf-8')
    logging.info('RAID status: ' + status)
  except Exception as e:
    logging.error('Failed to get RAID status: ' + str(e))
    send_exception_mail(e)
    return None

  # get status from sample output
  failed_devices = status.split("Failed Devices : ")[1].split("\n")[0]
  logging.info('Failed devices: ' + failed_devices)
  if failed_devices != '0':
    logging.error('RAID contains failed devices...')
    html = "<code>" + status.replace('\n','<br>') + "</code>"
    send_mail.SendMessage(SENDER, TO, 'RAID contains failed devices', html, status)
    exit(2)
  
  state_array = status.split("State : ")[1].split("\n")[0].split(',')
  logging.info('RAID states: ' + str(state_array))
  if len(state_array) > 1:
    logging.warning("RAID contains multiple states...")
    html = "<code>" + status.replace('\n','<br>') + "</code>"  
    send_mail.SendMessage(SENDER, TO, 'RAID contains multiple states', html, status)
    exit(1)
  
  logging.info('RAID is OK')

if __name__ == '__main__':
  get_raid_status()