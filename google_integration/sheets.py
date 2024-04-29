import google.auth.exceptions
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


import os
from datetime import datetime   
import pytz
import logging


from utils.environment import (
    load_environment
)


load_environment()
logging.basicConfig(level=logging.INFO)


CREDENTIALS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'credentials.json')
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/gmail.send"]


def get_sheet_service(access_token):
    credentials = Credentials(token=access_token)
    return build('sheets', 'v4', credentials=credentials)


def find_sheet_id(service, spreadsheet_id, sheet_name):
    logging.info(f'Attempting to find sheet ID for {sheet_name} in spreadsheet {spreadsheet_id}.')
    try:
        spreadsheet_details = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        for sheet in spreadsheet_details.get('sheets', []):
            if sheet['properties']['title'] == sheet_name:
                return sheet['properties']['sheetId']
        return None
    except google.errors.HttpError as e:
        logging.error(f'Failed to retrieve sheet details for {sheet_name}: {e}')
        return None


def read_spreadsheet_data(access_token, spreadsheet_id, sheet_name):
    # logging.info(f'Reading data from spreadsheet: {spreadsheet_id}, sheet: {sheet_name}')
    service = get_sheet_service(access_token)
    try:
        request = service.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=f'{sheet_name}!A1:Z')
        values = request.execute().get('values', [])
        if values:
            return {'success': True, 'data': values}
        else:
            return {'success': False, 'message': 'No data found'}
    except Exception as e:
        logging.error(f'An error occurred when reading spreadsheet data: {str(e)}')
        return {'success': False, 'message': f'An error occurred: {str(e)}'}


def fetch_spreadsheet_data(access_token, spreadsheet_id, sheet_name):
    logging.info(f'Fetching data from spreadsheet {spreadsheet_id} from sheet {sheet_name}')
    response = read_spreadsheet_data(access_token, spreadsheet_id, sheet_name)
    if not response['success']:
        logging.error('Tried to fetch spreadsheet data using read spreadsheet data function but an error occurred')
        return [], response
    
    data = response['data']
    return data, None


def unique_col_values(access_token, spreadsheet_id, sheet_name, column):
    logging.info(f'Reading unique column values in sheet: {sheet_name} in spreadsheet: {spreadsheet_id}')
    values, err_message = fetch_spreadsheet_data(access_token, spreadsheet_id, sheet_name)
    if err_message:
        return err_message
    if not values:
        return {'success': False, 'message': 'Spreadsheet has no values. Please make sure it has at least a header row'}

    try:
        col_name_index = values[0].index(column)
    except ValueError:
        return {'success': False, 'message': f'Column {column} not found in spreadsheet headers'}

    unique_values = set()

    for row in values[1:]:
        if len(row) > col_name_index:
            col_value = row[col_name_index]
            unique_values.add(col_value)

    unique_groups_list = list(unique_values)
    unique_groups_list.sort()

    return {'success': True, 'data': unique_groups_list}


# TODO: Cannot insert null values
def append_row_to_spreadsheet(access_token, col_names, spreadsheet_id, sheet_name, json_data):
    logging.info(f'Appending row to sheet: {sheet_name} in spreadsheet: {spreadsheet_id}')
    service = get_sheet_service(access_token)
    check = is_compatible_with_spreadsheet(col_names, json_data)

    if not check['success']:
        return check

    row_values = [""] * len(col_names)
    for key, value in json_data.items():
        if key in col_names:  
            index = col_names.index(key)
            row_values[index] = value

    body = {"values": [row_values]}

    try:
        request = service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range=f'{sheet_name}!A1:Z',
            valueInputOption='USER_ENTERED',
            insertDataOption='INSERT_ROWS',
            body=body
        )
        response = request.execute()
        return {'success': True, 'message': 'Successfuly appended values to your Google spreadsheet', 'data': response}
    except Exception as e:
        logging.error(f'There was an error while trying to append data to your Google spreadsheet: {str(e)}')
        return {'success': False, 'message': f'There was an error while trying to append data to your Google spreadsheet: {str(e)}'}


def create_append_col_body_request(sheet_id, column_append_index, column_name):
    return {
        "requests": [
            {
                "appendDimension": {
                    "sheetId": sheet_id,
                    "dimension": "COLUMNS",
                    "length": 1
                }
            },
            {
                "updateCells": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": 0,
                        "endRowIndex": 1,
                        "startColumnIndex": column_append_index,
                        "endColumnIndex": column_append_index + 1
                    },
                    "rows": [
                        {
                            "values": [
                                {
                                    "userEnteredValue": {
                                        "stringValue": column_name
                                    }
                                }
                            ]
                        }
                    ],
                    "fields": "userEnteredValue"
                }
            },
        ]
    }


def append_col_to_spreadsheet(access_token, spreadsheet_id, sheet_name, col_name):
    logging.info(f'Appending new column {col_name} to sheet {sheet_name} in spreadsheet {spreadsheet_id}.')
    service = get_sheet_service(access_token)
    
    sheet_id = find_sheet_id(service=service, spreadsheet_id=spreadsheet_id, sheet_name=sheet_name)
    if sheet_id is None:
        return {'success': False, 'message': 'Sheet name not found'}

    values, err_message = fetch_spreadsheet_data(access_token, spreadsheet_id, sheet_name)
    if err_message:
        return err_message
    if not values:
        return {'success': False, 'message': 'Spreadsheet has no values. Please make sure it has at least a header row'}

    if col_name in values[0]:
        return {'success': False, 'message': 'Column with that name already exists'}

    num_columns = len(values[0])
    request_body = create_append_col_body_request(sheet_id=sheet_id, column_append_index=num_columns, column_name=col_name)

    try:
        response = service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body=request_body
        ).execute()
        return {'success': True, 'message': f'Successfuly appended a column with name {col_name}'}
    except Exception as e:
        logging.error(f'Failed to append column {col_name}: {e}')
        return {'success': False, 'message': f'There was an error while trying to append column and set column name: {str(e)}'}


def add_attendance_bool_rows(access_token, spreadsheet_id, sheet_name, date_from_client, json_data, NAME_COLUMN="Imię", SURNAME_COLUMN="Nazwisko", GROUP_COLUMN="Grupa", ATTENDANCE_NAME="attendance"):
    service = get_sheet_service(access_token)
    sheet_id = find_sheet_id(service=service, spreadsheet_id=spreadsheet_id, sheet_name=sheet_name)
    if sheet_id is None:
        return {'success': False, 'message': 'Sheet name not found'}

    values, err_message = fetch_spreadsheet_data(access_token, spreadsheet_id, sheet_name)
    if err_message:
        return err_message
    if not values:
        return {'success': False, 'message': 'Spreadsheet has no values. Please make sure it has at least a header row'}

    date_validation_response = validate_attendance_date(date_from_client=date_from_client, columns_already_in_spreadsheet=[col.strip() for col in values[0]])
    if not date_validation_response['success']:
        return date_validation_response

    update_request = build_update_requests(access_token=access_token,
                                           spreadsheet_id=spreadsheet_id,
                                           values=values, 
                                           json_data=json_data,
                                           sheet_id=sheet_id,
                                           date_column=date_from_client,
                                           NAME_COLUMN=NAME_COLUMN,
                                           SURNAME_COLUMN=SURNAME_COLUMN,
                                           GROUP_COLUMN=GROUP_COLUMN,
                                           ATTENDANCE_NAME=ATTENDANCE_NAME)
    return update_request


def build_update_requests(access_token, spreadsheet_id, values, json_data, sheet_id, date_column, NAME_COLUMN, SURNAME_COLUMN, GROUP_COLUMN, ATTENDANCE_NAME):
    """Build requests for updating attendance in the spreadsheet."""

    requests = []
    columns = [col.strip() for col in values[0]]
    try:
        date_col_index = columns.index(date_column)
        name_index, surname_index, group_index = columns.index(NAME_COLUMN), columns.index(SURNAME_COLUMN), columns.index(GROUP_COLUMN)

        for student in json_data:
            row_index = find_student_row_index_for_attendance(values, student, name_index, surname_index, group_index, NAME_COLUMN, SURNAME_COLUMN, GROUP_COLUMN)
            if row_index is not None:
                attendance_value = student.get(ATTENDANCE_NAME, False) 
                requests.append(create_attendance_cell_update_request(sheet_id, row_index, date_col_index, attendance_value))
                logging.info(f"Updated attendance for {student[NAME_COLUMN]} {student[SURNAME_COLUMN]} in group {student[GROUP_COLUMN]}")

        if requests:
            service = get_sheet_service(access_token)
            response = service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests}).execute()
            return {'success': True, 'message': f'Attendance updated successfully. Students updated: {len(requests)}'}
        else:
            return {'success': False, 'message': 'No students were added for attendance update'}
    except Exception as e:
        return {'success': False, 'message': f'Unexpected error occurred: {str(e)}'}


def find_student_row_index_for_attendance(values, student, name_index, surname_index, group_index, NAME_COLUMN="Imię", SURNAME_COLUMN="Nazwisko", GROUP_COLUMN='Grupa'):
    """
    Find the row index for a given student in the spreadsheet data.
    """
    for i, row in enumerate(values[1:], start=1):
        row_name = row[name_index].strip() if len(row) > name_index else ''
        row_surname = row[surname_index].strip() if len(row) > surname_index else ''
        row_group = row[group_index].strip() if len(row) > group_index else ''
        if [str(row_name), str(row_surname), str(row_group)] == [str(student[NAME_COLUMN]), str(student[SURNAME_COLUMN]), str(student[GROUP_COLUMN])]:
            return i
    
    logging.warning(f'Student with name {student[NAME_COLUMN]} surname {student[SURNAME_COLUMN]} on group {student[GROUP_COLUMN]} was not found in spreadsheet for attendance')
    return None


def create_attendance_cell_update_request(sheet_id, row_index, column_index, attendance_value):
    return {
    "repeatCell": {
        "range": {
            "sheetId": sheet_id,
            "startRowIndex": row_index,  
            "endRowIndex": row_index + 1,
            "startColumnIndex": column_index,
            "endColumnIndex": column_index + 1
        },
        "cell": {
            "dataValidation": {
                "condition": {
                    "type": "BOOLEAN"
                },
                "showCustomUi": True
            },
            "userEnteredValue": {
                "boolValue": attendance_value
            }
        },
        "fields": "dataValidation,userEnteredValue.boolValue"
    }
    }

# TODO zrobic to
def validate_attendance_date(date_from_client, columns_already_in_spreadsheet):
    poland_timezone = pytz.timezone('Europe/Warsaw')
    utc_now = datetime.now(pytz.utc)
    poland_now = utc_now.astimezone(poland_timezone).date()

    if date_from_client:
        try:
            specific_date = datetime.strptime(date_from_client, '%d-%m-%Y').replace(tzinfo=poland_timezone).date()
            if specific_date > poland_now:
                return {'success': False, 'message': 'Future dates not allowed'}
        except ValueError:
            return {'success': False, 'message': 'Invalid date format. Use DD-MM-YYYY'}
    else:
        return {'success': False, 'message': 'Date has not been provided'}
    
    date_col_name = specific_date.strftime('%d-%m-%Y')
    if date_col_name not in columns_already_in_spreadsheet:
        return {'success': False, 'message': 'Can not read attendance from a date that is not in columns of an attendance list'}

    return {'success': True, 'message': 'Attendance date is valid'}


def validate_attendance_date_for_today(date_from_client):
    poland_timezone = pytz.timezone('Europe/Warsaw')
    utc_now = datetime.now(pytz.utc)
    poland_now = utc_now.astimezone(poland_timezone).date()

    if date_from_client:
        try:
            specific_date = datetime.strptime(date_from_client, '%d-%m-%Y').replace(tzinfo=poland_timezone).date()
            if specific_date == poland_now:
                return {'success': True, 'message': 'Provided date is valid to create an attendance for today'}
            elif specific_date > poland_now:
                return {'success': False, 'message': 'Future dates not allowed'}
            elif specific_date < poland_now:
                return {'success': False, 'message': 'Earlier dates than today are not allowed for creating attendance check for today'}

        except ValueError:
            return {'success': False, 'message': 'Invalid date format. Use DD-MM-YYYY'}
    else:
        return {'success': False, 'message': 'Date has not been provided'}


def parse_and_validate_attendance(access_token, spreadsheet_id, sheet_name, date_from_client, group_filter=None, NAME_COLUMN="Imię", SURNAME_COLUMN="Nazwisko", GROUP_COLUMN="Grupa"):
    service = get_sheet_service(access_token)
    sheet_id = find_sheet_id(service, spreadsheet_id, sheet_name)
    if sheet_id is None:
        logging.error("Sheet name not found.")
        return {'success': False, 'message': 'Sheet name not found'}

    values, err_message = fetch_spreadsheet_data(access_token, spreadsheet_id, sheet_name)
    if err_message:
        logging.error(f"Error fetching data: {err_message}")
        return err_message
    if not values:
        logging.error("No values found in the spreadsheet.")
        return {'success': False, 'message': 'Spreadsheet has no values. Please make sure it has at least a header row'}

    columns = [col.strip() for col in values[0]]
    valid_date = validate_attendance_date(date_from_client=date_from_client, columns_already_in_spreadsheet=columns)
    if not valid_date['success']:
        logging.error(f"Invalid date: {valid_date['message']}")
        return valid_date

    try:
        date_col_index = columns.index(date_from_client.strip())
        name_index = columns.index(NAME_COLUMN)
        surname_index = columns.index(SURNAME_COLUMN)
        group_index = columns.index(GROUP_COLUMN)

        students_at_given_date = []
        for student in values[1:]:
            if len(student) == len(columns):
                student_info = fetch_student_info(student=student, 
                                                  group_filter=group_filter, 
                                                  group_index=group_index, 
                                                  name_index=name_index, 
                                                  surname_index=surname_index, 
                                                  NAME_COLUMN=NAME_COLUMN, 
                                                  SURNAME_COLUMN=SURNAME_COLUMN, 
                                                  GROUP_COLUMN=GROUP_COLUMN)
                if student_info:
                    student[date_col_index] = student[date_col_index] == 'TRUE'
                    student_info['attendance'] = student[date_col_index]
                    students_at_given_date.append(student_info)

        return {'success': True, 'data': students_at_given_date}
    except ValueError as e:
        logging.error(f"Value error in parsing data: {str(e)}")
        return {'success': False, 'message': f"Unexpected error occurred: {str(e)}"}
    except IndexError as e:
        logging.error(f"Index error in accessing list elements: {str(e)}")
        return {'success': False, 'message': f"Unexpected error occurred: {str(e)}"}



def fetch_student_info(student, group_filter, name_index, surname_index, group_index, NAME_COLUMN, SURNAME_COLUMN, GROUP_COLUMN):
    if group_filter and student[group_index] != group_filter:
        return None
    return {
        NAME_COLUMN: student[name_index],
        SURNAME_COLUMN: student[surname_index],
        GROUP_COLUMN: student[group_index]
    }


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