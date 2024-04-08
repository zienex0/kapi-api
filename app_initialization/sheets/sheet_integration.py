from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow, Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from app_initialization import cache

import json
import os
import requests
from dotenv import load_dotenv
import logging
import base64
from email.mime.text import MIMEText


ENV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
load_dotenv(ENV_PATH)

logging.basicConfig(level=logging.INFO)


CREDENTIALS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'credentials.json')
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/gmail.send"]


flow = Flow.from_client_secrets_file(
    CREDENTIALS_PATH, 
    scopes=SCOPES,
    redirect_uri='https://zienex.pythonanywhere.com/auth-callback'
    )


def get_valid_access_token():
    access_token = cache.get('access_token')
    if access_token and is_access_token_valid(access_token):
        logging.info('Access token is valid. Using this cached token...')
        return access_token

    else:
        logging.info('Access token not valid or not cached. Refreshing token...')
        token = refresh_access_token(refresh_token=os.getenv('REFRESH_TOKEN'))
        cache.set('access_token', token)
        return token


def refresh_access_token(refresh_token, credentials_path=CREDENTIALS_PATH):
    """
    Uses refresh token that is connected with Google account
    and app credentials in order to create an access token
    """
    with open(credentials_path, 'r') as f:
        credentials_info = json.load(f)['web']

    client_id = credentials_info['client_id']
    client_secret = credentials_info['client_secret']
    credentials = Credentials(
        None,  
        refresh_token=refresh_token,
        token_uri='https://oauth2.googleapis.com/token',
        client_id=client_id,
        client_secret=client_secret
    )

    request = Request()
    credentials.refresh(request)

    return credentials.token


def is_access_token_valid(access_token):
    response = requests.get('https://www.googleapis.com/oauth2/v3/tokeninfo', params={'access_token': access_token})
    if response.ok:
        return True
    else:
        return False


def read_spreadsheet_data(access_token, spreadsheet_id, range_name):
    creds = Credentials(token=access_token)
    service = build('sheets', 'v4', credentials=creds)

    sheet = service.spreadsheets()
    result = (
        sheet.values()
        .get(spreadsheetId=spreadsheet_id, range=range_name)
        .execute()
    )
    if result:
        values = result.get("values", [])
        return {'success': True, 'data': values}
    else:
        return {'success': False, 'message': 'There was an error while trying to recieve data from your Google spreadsheet'}

def unique_col_values(access_token, spreadsheet_id, range_name, column):
    response = read_spreadsheet_data(access_token, spreadsheet_id, range_name)
    if response['success']:
        spreadsheet_data = response['data']
        col_name_index = spreadsheet_data[0].index(column)
        unique_values = set()

        for row in spreadsheet_data[1:]:
            col_value = row[col_name_index]
            unique_values.add(col_value)

        unique_groups_list = list(unique_values)
        unique_groups_list.sort()
        return {'success': True, 'data': unique_groups_list}
    else:
        return response

# TODO: Cannot insert null values
def append_row_to_spreadsheet(access_token, col_names, spreadsheet_id, range_name, json_data):
    check = is_compatible_with_spreadsheet(col_names, json_data)
    if check['success']:
        creds = Credentials(token=access_token)
        service = build('sheets', 'v4', credentials=creds)

        row_values = [""] * len(col_names)
        for key, value in json_data.items():
            if key in col_names:  
                index = col_names.index(key)
                row_values[index] = value

        body = {"values": [row_values]}
        sheet = service.spreadsheets()
        result = (
            sheet.values()
            .append(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption='USER_ENTERED',
                body=body,
            )
            .execute()
        )
        if result:
            return {'success': True, 'message': 'Successfuly appended values to your Google spreadsheet'}
        else:
            return {'success': False, 'message': 'There was an error while trying to append data to your Google spreadsheet'}
    else:
        return check


def is_compatible_with_spreadsheet(spread_col_names, json_data):
    """
    Checks wether json data can be inserted into a spreadsheet
    """

    spreadsheet_keys = set(spread_col_names)
    json_keys = set(json_data.keys())

    if json_keys == spreadsheet_keys:
        return {"success": True, "message": "JSON data is compatible with the spreadsheet."}
    else:
        missing_keys = spreadsheet_keys - json_keys
        extra_keys = json_keys - spreadsheet_keys
        return {
            "success": False,
            "message": "JSON data is not compatible with the spreadsheet due to column mismatch.",
            "missing_keys": list(missing_keys),
            "extra_keys": list(extra_keys)
        }



def get_google_auth_url():
    auth_url, _ = flow.authorization_url(prompt='consent')
    return auth_url


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


def update_env_file(key, value, env_path=ENV_PATH):
    """Update an environment variable in a .env file. If the variable does not exist, add it."""
    if not os.path.isfile(env_path):
        with open(env_path, 'w'): pass
    lines = []
    with open(env_path, 'r') as file:
        lines = file.readlines()
    key_exists = False
    for i, line in enumerate(lines):
        if line.startswith(f'{key}='):
            lines[i] = f'{key}={value}\n'
            key_exists = True
            break
    if not key_exists:
        lines.append(f'{key}={value}\n')
    with open(env_path, 'w') as file:
        file.writelines(lines)
