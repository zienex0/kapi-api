import base64
from email.mime.text import MIMEText
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


import logging


def create_message(sender, to, subject, message_text):
    if isinstance(to, list):
        to = ', '.join(to)

    message = MIMEText(message_text)
    message['to'] = to
    message['from'] = sender
    message['subject'] = subject
    return {'raw': base64.urlsafe_b64encode(message.as_string().encode()).decode()}


def send_email(access_token, sender, to, subject, message_text):
    logging.info(f'Sending email to {to} from {sender} with subject {subject}.')
    credentials = Credentials(token=access_token)
    service = build('gmail', 'v1', credentials=credentials)
    message = create_message(sender, to, subject, message_text)
    try:
        message = (service.users().messages().send(userId='me', body=message).execute())
        return {'success': True, 'message': 'Mail sent successfuly'}
    except Exception as error:
        logging.error(f'Email sending failed: {error}')
        return {'success': False, 'message': 'An error occurred while sending mail'}    