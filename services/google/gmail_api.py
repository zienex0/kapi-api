import base64
import mimetypes
import os
from email.message import EmailMessage
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import json


def send_mail(creds, to, from_email, subject, body, attachment_path):
    try:
        service = build("gmail", "v1", credentials=creds)
        mime_message = EmailMessage()
        
        mime_message["To"] = to
        mime_message["From"] = from_email
        mime_message["Subject"] = subject
        
        mime_message.set_content(body)
        
        if attachment_path and os.path.isfile(attachment_path):
            type_subtype, _ = mimetypes.guess_type(attachment_path)
            maintype, subtype = type_subtype.split("/")
            
            with open(attachment_path, "rb") as fp:
                attachment_data = fp.read()
            mime_message.add_attachment(attachment_data, maintype, subtype)
        
        encoded_message = base64.urlsafe_b64encode(mime_message.as_bytes()).decode()
        create_message = {"raw": encoded_message}
        
        send_message = service.users().messages().send(userId="me", body=create_message).execute()
        print(f'Message Id: {send_message["id"]}')
    except HttpError as error:
        print(f"An error occurred: {error}")
        send_message = None
        
    return send_message

