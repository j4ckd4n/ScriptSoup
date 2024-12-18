import httplib2
import os
import oauth2client
from oauth2client import client, tools, file
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from apiclient import errors, discovery
import argparse
import sys

SCOPES = 'https://www.googleapis.com/auth/gmail.send'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'Gmail API Python Send Email'

def get_credentials():
  home_dir = os.path.expanduser('~')
  credential_dir = os.path.join(home_dir, '.credentials')
  if not os.path.exists(credential_dir):
    os.makedirs(credential_dir)
  credential_path = os.path.join(credential_dir, 'gmail-python-email-send.json')
  store = file.Storage(credential_path)
  credentials = store.get()
  if not credentials or credentials.invalid:
    flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
    flow.user_agent = APPLICATION_NAME
    credentials = tools.run_flow(flow, store)
    print('Storing credentials to ' + credential_path)
  return credentials

def SendMessage(sender, to, subject, msgHtml, msgPlain):
  credentials = get_credentials()
  http = credentials.authorize(httplib2.Http())
  service = discovery.build('gmail', 'v1', http=http)
  message1 = CreateMessage(sender, to, subject, msgHtml, msgPlain)
  SendMessageInternal(service, "me", message1)

def SendMessageInternal(service, user_id, message):
  try:
    message = (service.users().messages().send(userId=user_id, body=message).execute())
    print('Message Id: %s' % message['id'])
    return message
  except errors.HttpError as error:
    print('An error occurred: %s' % error)

def CreateMessage(sender, to, subject, msgHtml, msgPlain):
  msg = MIMEMultipart('alternative')
  msg['Subject'] = subject
  msg['From'] = sender
  msg['To'] = to
  msg.attach(MIMEText(msgPlain, 'plain'))
  msg.attach(MIMEText(msgHtml, 'html'))
  raw = base64.urlsafe_b64encode(msg.as_bytes())
  raw = raw.decode()
  body = {'raw': raw}
  return body


def main(to, sender, subject, msgPlain):
  msgHtml = msgPlain
  # replace all newlines with <br> tag
  msgHtml = msgHtml.replace('\n', '<br>')
  SendMessage(sender, to, subject, msgHtml, msgPlain)
  # Send message with attachment: 
  # SendMessage(sender, to, subject, msgHtml, msgPlain, '/path/to/file.pdf')

if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='Send email using Gmail API')
  parser.add_argument('-t', '--to', required=True, help='Recipient email address')
  parser.add_argument('-s', '--subject', required=True, help='Email subject')
  parser.add_argument('-m', '--message', required=False, help='Email message')

  args = parser.parse_args()

  message = args.message
  if not sys.stdin.isatty():
    msgPlain = sys.stdin.read()
    print("Message body: " + msgPlain)
    message = msgPlain

  sender = "sender@example.com"

  main(args.to, sender, args.subject, message)