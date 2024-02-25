import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
import json


def get_google_token(scopes):
    """
    Retrieves or refreshes Google API credentials, handling both new authorization and existing token refresh scenarios.

    Attempts to construct a `Credentials` object using environment variables. If credentials are invalid or absent,
    it either refreshes the token using a refresh token or initiates an authorization flow for installed applications.
    Successful authentication updates the access token in environment variables and returns the credentials object.

    :param scopes: A list of strings specifying the Google API scopes needed for the credentials.
    :type scopes: list

    :return: A `Credentials` object for accessing Google APIs.
    :rtype: google.oauth2.credentials.Credentials

    Environment Variables:
    - GOOGLE_TOKEN: Current access token.
    - GOOGLE_REFRESH_TOKEN: Refresh token to obtain a new access token.
    - GOOGLE_TOKEN_URI: Endpoint URI for obtaining tokens.
    - GOOGLE_CLIENT_ID: Client ID for Google API application.
    - GOOGLE_CLIENT_SECRET: Client secret for Google API application.
    - GOOGLE_PROJECT_ID: (Optional) Project ID for the Google API application.
    - GOOGLE_AUTH_URI: Authorization endpoint URI.
    - GOOGLE_AUTH_PROVIDER_X509_CERT_URL: URL of the public certificate for token verification.
    - GOOGLE_REDIRECT_URIS: Comma-separated list of redirect URIs.
    """
    
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