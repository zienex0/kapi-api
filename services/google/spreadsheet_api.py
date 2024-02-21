from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import json


def read_spreadsheet_data(creds, spreadsheet_id, range_name):
    """
    Initializes the Google Sheets service using credentials. Reads the Google Sheet data as returns it as json.

    :param creds: Google Sheets API credentials required to create the Google Sheets service.
    :param spreadsheet_id: The Google Sheet ID of your sheet.
    :param range_name: Name of the sheet and range where values will be places - in our case 'Arkusz1'
    """
    
    try:
        service = build("sheets", "v4", credentials=creds)
        sheet = service.spreadsheets()
        result = (
            sheet.values()
            .get(spreadsheetId=spreadsheet_id, range=range_name)
            .execute()
        )
        col_names = read_spreadsheet_columns(creds=creds, spreadsheet_id=spreadsheet_id, range_name=range_name)
        values = result.get("values", [])
        
        list_of_json_values = []
        for row in range(1, len(values)):
            row_values = {col_names[i]:values[row][i] for i in range(len(col_names))}
            list_of_json_values.append(row_values)
        
        json_values = json.dumps(list_of_json_values)
        return json_values
    
    except HttpError as err:
        print(err)


def read_spreadsheet_columns(creds, spreadsheet_id, range_name):
    """
    Reads the first row of the Google spreadsheet and returns it. 
    In other words, function returns the column names of the spreadsheet.

    :param creds: Google Sheets API credentials required to create the Google Sheets service.
    :param spreadsheet_id: The Google Sheet ID of your sheet.
    :param range_name: Name of the sheet and range where values will be places - in our case 'Arkusz1'    
    """

    try:
        service = build("sheets", "v4", credentials=creds)
        sheet = service.spreadsheets()
        result = (
            sheet.values()
            .get(spreadsheetId=spreadsheet_id, range=range_name + "!1:1")
            .execute()
        )
        col_names = result.get("values", [])[0] if result.get("values") else []
        return col_names
    
    except HttpError as err:
        print(err)
        return []

def append_row_to_spreadsheet(creds, spreadsheet_id, range_name, json_data):
    """
    Initializes the Google Sheets service using credentials and appends a row of values
    to the specified spreadsheet. This requires Google project API credentials and correct column names
    with attached values to them.

    
    :param creds: Google Sheets API credentials required to create the Google Sheets service.
    :param spreadsheet_id: The Google Sheet ID of your sheet.
    :param range_name: Name of the sheet and range where values will be places - in our case 'Arkusz1'
    :param json_data: A json that contains column names with attached values in order to append it to a spreadsheet.
    """
    try:
        col_names = read_spreadsheet_columns(creds=creds, spreadsheet_id=spreadsheet_id, range_name=range_name)

        # Map the values to corresponding columns from the json data
        row_values = [""] * len(col_names)
        for key, value in json_data.items():
            index = col_names.index(key)
            row_values[index] = value

        service = build("sheets", "v4", credentials=creds)

        body = {"values": [row_values]}

        result = (
            service.spreadsheets().values()
            .append(spreadsheetId=spreadsheet_id, range=range_name,
                    valueInputOption="USER_ENTERED", body=body)
            .execute()
        )

        return result
    
    except HttpError as err:
        print(err)
        return