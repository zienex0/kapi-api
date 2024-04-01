from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import base64
from email.mime.text import MIMEText


def create_message(sender, to, subject, message_text):
    if isinstance(to, list):
        to = ', '.join(to)

    message = MIMEText(message_text)
    message['to'] = to
    message['from'] = sender
    message['subject'] = subject
    return {'raw': base64.urlsafe_b64encode(message.as_string().encode()).decode()}

def send_email(access_token, sender, to, subject, message_text):
    credentials = Credentials(token=access_token)
    service = build('gmail', 'v1', credentials=credentials)
    message = create_message(sender, to, subject, message_text)
    try:
        message = (service.users().messages().send(userId='me', body=message).execute())
        return {'success': True, 'message': 'Mail sent successfuly'}
    except Exception as error:
        return {'success': False, 'message': 'An error occurred while sending mail'}
