import os
from dotenv import load_dotenv
from flask import request

from flask import Flask, redirect
from google_auth_oauthlib.flow import Flow

from . import app
from app_initialization.sheets.sheet_integration import (
    read_spreadsheet_data, 
    unique_col_values,
    append_row_to_spreadsheet,
    get_valid_access_token,
    get_google_auth_url,
    flow,
    send_email,
    update_env_file
)

from utils import (
    pretty_json_response,
)

load_dotenv()
SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')
ARKUSZ_UCZNIOWIE = 'Arkusz1'
ARKUSZ_LISTA_OBECNOŚCI = 'Lista obecności'
KOLUMNA_GRUP = 'Grupa'


@app.route('/', methods=['GET'])
def home_endpoints():
    routes = []
    for rule in app.url_map.iter_rules():
        if 'GET' in rule.methods and not rule.endpoint == 'static':
            routes.append(f"{rule.rule}")
    return pretty_json_response(routes)

@app.route('/get-auth-url', methods=['GET'])
def get_auth_url():
    auth_url = get_google_auth_url()
    return pretty_json_response({'auth_url': auth_url})


@app.route('/auth-callback')
def handle_auth_callback():
    flow.fetch_token(authorization_response=request.url)
    credentials = flow.credentials
    if credentials.refresh_token:
        update_env_file(key='REFRESH_TOKEN', value=f'"{credentials.refresh_token}"')
        return pretty_json_response({'success': True, 'message': 'Logged in successful'})
    else:
        return pretty_json_response({'success': False, 'message': 'Login not successful. Your refresh token was not recieved'})

# TODO: filter the func
@app.route('/all-students', methods=['GET'])
def students_data():
    token = get_valid_access_token()
    students_info = read_spreadsheet_data(access_token=token, spreadsheet_id=SPREADSHEET_ID, range_name=ARKUSZ_UCZNIOWIE)
    if students_info['success']:
        return pretty_json_response(students_info['data'])
    else:
        return pretty_json_response(students_info, 400)

# TODO: Make choose the groups col name 
@app.route('/available-groups', methods=['GET'])
def student_groups():
    token = get_valid_access_token()
    student_group_col_name = KOLUMNA_GRUP
    col_values = unique_col_values(access_token=token, spreadsheet_id=SPREADSHEET_ID, range_name=ARKUSZ_UCZNIOWIE, column=student_group_col_name)
    if col_values['success']:
        return pretty_json_response(col_values['data'])
    else:
        return pretty_json_response(col_values, 400)

@app.route('/filter-by-group', methods=['GET'])
def students_by_groups():
    desired_group = request.args.get('group', default=None, type=int)
    if not desired_group:
        message = {"success": False, "message": "Group name is required as a query parameter"}
        return pretty_json_response(message, 400)
    desired_group = str(desired_group)

    token = get_valid_access_token()
    response = read_spreadsheet_data(token, SPREADSHEET_ID, ARKUSZ_UCZNIOWIE)
    if response['success']:
        spreadsheet_data = response['data']
        col_name_index = spreadsheet_data[0].index(KOLUMNA_GRUP)

        filtered_students = []
        for row in spreadsheet_data[1:]:
            if row[col_name_index] == desired_group:
                filtered_students.append(row)
        return pretty_json_response(filtered_students)
    else:
        return pretty_json_response(response, 400)


@app.route('/columns')
def col_types_names():
    """
    Temporary function. Right now it is hardcoded.
    In the future, the customer will decide column types to make training forms correct
    thus making editing correct.
    """

    types_names = {
    "Imię": "Name",
    "Nazwisko": "Surname",
    "Telefon": "Phone",
    "Mail": "Mail",
    "Rocznik": "Year",
    "Adres": "Adress",
    "Kod pocztowy": "PostalCode",
    "Grupa": "Group",
    "Rozmiar koszulki": "Size",
    "Uwagi": "Comments" ,
    "Zgoda na regulamin": "Agree",
    "Jednorazowy trening": "OneTimer",
    }

    return pretty_json_response(types_names)


@app.route('/add-student', methods=['POST'])
def add_student():
    new_student_data = request.json

    if not new_student_data:
        return pretty_json_response({'success': False, 'message': 'No data was sent'})

    token = get_valid_access_token()
    retrieve_students = read_spreadsheet_data(token, SPREADSHEET_ID, ARKUSZ_UCZNIOWIE)
    if retrieve_students['success']:
        col_names = retrieve_students['data'][0]
        append_data_response = append_row_to_spreadsheet(access_token=token,
                                                         col_names=col_names,
                                                         spreadsheet_id=SPREADSHEET_ID,
                                                         range_name=ARKUSZ_UCZNIOWIE,
                                                         json_data=new_student_data)
        if append_data_response['success']:
            mail_body = new_student_data
            mail = send_email(access_token=token, 
                              sender='szymon.zienkiewicz5@gmail.com', 
                              to=["wojtop@interia.pl", "szymon.zienkiewicz5@gmail.com"],
                              subject='Automatyczny mail po dostaniu formularza',
                              message_text=f'Ten mail został wysłany automatycznie, nie odpisuj na niego.\nOtrzymaliśmy nowy wypełniony formularz, zarejestrował się nowy uczestnik!\n\n{mail_body}')

            return pretty_json_response(mail)

        else:
            # appending not successful
            return pretty_json_response(append_data_response, 400)
    else:
        # reading the students data not successful
        return pretty_json_response(retrieve_students, 400)