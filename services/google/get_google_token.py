import json
import os
import requests
from dotenv import load_dotenv
import logging

from google_auth_oauthlib.flow import InstalledAppFlow

env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
load_dotenv(env_path)

logging.basicConfig(level=logging.INFO)


CREDENTIALS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'credentials.json')
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/gmail.send"]

def get_credentials(creds_path, scopes):
    flow = InstalledAppFlow.from_client_secrets_file(creds_path, scopes)
    creds = flow.run_local_server(port=0)
    return creds


def update_env_file(env_path, key, value):
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

def get_access_token():
    """
    Uses refresh token that is connected with one's Google account
    and app credentials in order to create an access token
    """
    with open(CREDENTIALS_PATH, 'r') as f:
        credentials = json.load(f)['installed']

    client_id = credentials['client_id']
    client_secret = credentials['client_secret']
    refresh_token = os.getenv('REFRESH_TOKEN')
    params = {
        'client_id': client_id,
        'client_secret': client_secret,
        'refresh_token': refresh_token,
        'grant_type': 'refresh_token',
    }
    token_url = 'https://oauth2.googleapis.com/token'
    response = requests.post(token_url, data=params)
    return response.json().get('access_token')

if __name__ == '__main__':
    creds = get_credentials(CREDENTIALS_PATH, SCOPES)
    CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(os.path.dirname(os.path.dirname(CURRENT_DIR)), '.env')
    refresh_token = "'" + creds.refresh_token + "'"
    update_env_file(env_path, 'REFRESH_TOKEN', refresh_token)
    print('Refresh token recieved and saved in .env file')

