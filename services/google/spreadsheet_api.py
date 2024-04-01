from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


def read_spreadsheet_data(access_token, spreadsheet_id, range_name):
    creds = Credentials(token=access_token)
    service = build("sheets", "v4", credentials=creds)

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


def append_row_to_spreadsheet(access_token, col_names, spreadsheet_id, range_name, json_data):
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
