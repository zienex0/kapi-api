import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
import json


def get_google_token(scopes):
    creds = None

    token_info = {
        "token": os.getenv("GOOGLE_TOKEN"),
        "refresh_token": os.getenv("GOOGLE_REFRESH_TOKEN"),
        "token_uri": os.getenv("GOOGLE_TOKEN_URI"),
        "client_id": os.getenv("GOOGLE_CLIENT_ID"),
        "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
        "scopes": scopes,
    }


    if all(value is not None for value in token_info.values()):
        creds = Credentials.from_authorized_user_info(token_info, scopes)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Load the client configuration from environment variables
            client_config = {
                "installed": {
                    "client_id": os.getenv("GOOGLE_CLIENT_ID"),
                    "project_id": os.getenv("GOOGLE_PROJECT_ID", ""),
                    "auth_uri": os.getenv("GOOGLE_AUTH_URI"),
                    "token_uri": os.getenv("GOOGLE_TOKEN_URI"),
                    "auth_provider_x509_cert_url": os.getenv("GOOGLE_AUTH_PROVIDER_X509_CERT_URL"),
                    "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
                    "redirect_uris": os.getenv("GOOGLE_REDIRECT_URIS").split(","),
                }
            }
            flow = InstalledAppFlow.from_client_config(client_config, scopes)
            creds = flow.run_local_server(port=0)

        # Optionally, update the environment variables instead of writing to token.json
        os.environ["GOOGLE_TOKEN"] = creds.token
        # Consider securely saving refresh tokens if they are part of the response

    return creds