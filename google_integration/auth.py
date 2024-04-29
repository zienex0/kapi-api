import google.auth.exceptions
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials


import os
import json
import requests
import logging

from app_initialization import cache

logging.basicConfig(level=logging.INFO)


CREDENTIALS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'credentials.json')
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/gmail.send"]


def get_google_auth_url():
    flow = create_google_flow()
    if flow is None:
        return None
    auth_url, _ = flow.authorization_url(prompt='consent')
    return auth_url


def create_google_flow():
    try:
        flow = Flow.from_client_secrets_file(
            CREDENTIALS_PATH, 
            scopes=SCOPES,
            redirect_uri='https://zienex.pythonanywhere.com/auth-callback'
            )
        return flow
    except Exception as e:
        logging.error(f'Error occurred while creating Google flow: {str(e)}')
        return None


def is_access_token_valid(access_token):
    response = requests.get('https://www.googleapis.com/oauth2/v3/tokeninfo', params={'access_token': access_token})
    if response.ok:
        return True
    else:
        return False


def get_valid_access_token(cached_token):
    access_token = cached_token
    if access_token and is_access_token_valid(access_token):
        logging.info('Access token is valid.')
        return access_token

    else:
        logging.warning('Access token not valid or not cached. Refreshing token...')
        token = refresh_access_token(refresh_token=os.getenv('REFRESH_TOKEN'))
        if token:
            cache.set('access_token', token)
            logging.info('Access token refreshed and cached.')
        else:
            logging.error('Failed to refresh access token.')
        return token


def refresh_access_token(refresh_token, credentials_path=CREDENTIALS_PATH):
    """
    Uses refresh token that is connected with Google account
    and app credentials in order to create an access token
    """
    logging.info('Attempting to refresh access token...')

    with open(credentials_path, 'r') as f:
        credentials_info = json.load(f)['web']

    client_id = credentials_info['client_id']
    client_secret = credentials_info['client_secret']
    try:
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

    except google.auth.exceptions.RefreshError as e:
        logging.error(f"Failed to refresh token: {str(e)}")
        # Consider a mechanism to notify the system or the user that re-authentication is required.
        return None
    except Exception as e:
        logging.error(f'An unexpected error occurred during refreshing an access token: {str(e)}')
        return None

