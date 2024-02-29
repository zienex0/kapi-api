import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow


def get_google_token(scopes):
    """
    Retrieves or refreshes Google API credentials, handling both new authorization and existing token refresh scenarios.

    Attempts to construct a `Credentials` object using environment variables. If credentials are invalid or absent,
    it either refreshes the token using a refresh token or initiates an authorization flow for installed applications.
    Successful authentication updates the access token in environment variables and returns the credentials object.

    :param scopes: A list of strings specifying the Google API scopes needed for the credentials.
    """
    
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", scopes)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", scopes
            )
            creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open("token.json", "w") as token:
                token.write(creds.to_json())
    return creds