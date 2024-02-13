import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

SPREADSHEET_ID = "14GrMsrgj_Uz8bZnAcZm68PjWsU1dXvVj5kUuZccZYxs"

def establish_connection_with_google_sheet(scopes, spreadsheet_id):
  creds = None
  if os.path.exists("token.json"):
    creds = Credentials.from_authorized_user_file("token.json", SCOPES)

  if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
      creds.refresh(Request())
    else:
      flow = InstalledAppFlow.from_client_secrets_file(
          "credentials.json", scopes
      )
      creds = flow.run_local_server(port=0)

    with open("token.json", "w") as token:
      token.write(creds.to_json())

  try:
    service = build("sheets", "v4", credentials=creds)

    sheet = service.spreadsheets()
    result = (
        sheet.values()
        .get(spreadsheetId=spreadsheet_id, range="Arkusz1")
        .execute()
    )
    values = result.get("values", [])

    if not values:
      print("No data found.")
      return

    print("dane z tabelki:")
    for row in values:
        print(row)
  except HttpError as err:
    print(err)


if __name__ == "__main__":
  establish_connection_with_google_sheet(SCOPES, SPREADSHEET_ID)