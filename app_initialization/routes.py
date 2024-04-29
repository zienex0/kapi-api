import os
from flask import request
from functools import wraps

from . import app, cache
from google_integration.sheets import (
    read_spreadsheet_data, 
    unique_col_values,
    append_row_to_spreadsheet,
    fetch_spreadsheet_data,
    append_col_to_spreadsheet,
    add_attendance_bool_rows,
    validate_attendance_date_for_today,
    parse_and_validate_attendance,
)

from google_integration.auth import (
    get_valid_access_token,
    get_google_auth_url,
    create_google_flow,
)

from google_integration.email import (
    send_email,
)

from utils.general_utils import (
    pretty_json_response,
    fields_not_empty,
    make_cache_key
)

from utils.environment import (
    load_environment,
    update_env_file
)

load_environment()

SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')
ARKUSZ_UCZNIOWIE = 'Arkusz1'
ARKUSZ_LISTA_OBECNOŚCI = 'Lista obecności'
KOLUMNA_GRUP = 'Grupa'


def fetch_valid_token(access_func):
    @wraps(access_func)
    def wrapper(*args, **kwargs):
        token = get_valid_access_token(cache.get('access_token'))
        if not token:
            return pretty_json_response({'success': False, 'message': 'Failed to obtain valid access token. Try logging in with your Google account once again'}, 401)
        try:
            return access_func(token, *args, **kwargs)
        except Exception as e:
            return pretty_json_response({'success': False, 'message': str(e)}, 500)
    wrapper.__name__ = f"{access_func.__name__}_endpoint"
    return wrapper


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
    """
    Get the response from Google auth callback.
    Save the refresh token so can generate new valid access tokens
    for Google API
    """
    flow = create_google_flow()
    if flow is None:
        return pretty_json_response({'success': False, 'message': 'Failed to create Google auth flow'})

    flow.fetch_token(authorization_response=request.url)
    credentials = flow.credentials
    if credentials.refresh_token:
        resp = update_env_file(key='REFRESH_TOKEN', value=f'"{credentials.refresh_token}"')
        if resp['success']:
            return pretty_json_response({'success': True, 'message': 'Logged in successful'})
        else:
            return pretty_json_response({'success': False, 'message': 'Failed to save Google account refresh token for app'}, 500)
    else:
        return pretty_json_response({'success': False, 'message': 'Login not successful. Your refresh token was not recieved'})


@app.route('/all-students', methods=['GET'])
@fetch_valid_token
@cache.cached(timeout=50, key_prefix=make_cache_key)
def students_data(token):
    students_info = read_spreadsheet_data(access_token=token, spreadsheet_id=SPREADSHEET_ID, sheet_name=ARKUSZ_UCZNIOWIE)
    if students_info['success']:
        return pretty_json_response(students_info['data'])
    else:
        return pretty_json_response(students_info, 400)


# TODO: Make choose the groups col name 
@app.route('/available-groups', methods=['GET'])
@fetch_valid_token
@cache.cached(timeout=50, key_prefix=make_cache_key)
def student_groups(token):
    col_values = unique_col_values(access_token=token, spreadsheet_id=SPREADSHEET_ID, sheet_name=ARKUSZ_UCZNIOWIE, column=KOLUMNA_GRUP)
    if col_values['success']:
        return pretty_json_response(col_values['data'])
    else:
        return pretty_json_response(col_values, 400)


@app.route('/filter-by-group', methods=['GET'])
@fetch_valid_token
@cache.cached(timeout=50, key_prefix=make_cache_key)
def students_by_groups(token):
    desired_group = request.args.get('group', default=None)
    if not desired_group:
        message = {"success": False, "message": "Group name is required as a query parameter"}
        return pretty_json_response(message, 400)

    desired_group = str(desired_group)

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


@app.route('/attendance', methods=['GET'])
@fetch_valid_token
@cache.cached(timeout=30, key_prefix=make_cache_key)
def get_attendance(token):
    date = request.args.get('date', default=None)
    group_filter = request.args.get('group', default=None)

    if not date:
        return pretty_json_response({'success': False, 'message': "Missing 'date' parameter"}, 400)

    response = parse_and_validate_attendance(access_token=token,
                                             spreadsheet_id=SPREADSHEET_ID,
                                             sheet_name=ARKUSZ_LISTA_OBECNOŚCI,
                                             date_from_client=date,
                                             group_filter=group_filter)
    if not response['success']:
        return pretty_json_response(response, 400)
    
    return pretty_json_response(response)


@app.route('/attendance', methods=['POST'])
@fetch_valid_token
def add_or_update_attendance(token):
    """
    Adds attendance for today while no date is given. 
    Otherwise updates the attendance data on specified day in dd-mm-yyyy format.
    """
    attendance_data = request.get_json()
    if not attendance_data:
        return pretty_json_response({'success': False, 'message': 'No data provided'}, 400)

    date_from_client = request.args.get('date', default=None)
    if not date_from_client:
        return pretty_json_response({'success': False, 'message': "Missing 'date' parameter"}, 400)

    values, err_message = fetch_spreadsheet_data(access_token=token, spreadsheet_id=SPREADSHEET_ID, sheet_name=ARKUSZ_LISTA_OBECNOŚCI)
    if err_message:
        return err_message
    elif not values:
        return pretty_json_response({'success': False, 'message': 'Spreadsheet is empty'})
    
    date_valid_response = validate_attendance_date_for_today(date_from_client=date_from_client)
    if not date_valid_response['success']:
        return pretty_json_response(date_valid_response, 400)

    if date_from_client in values[0]:
        pass
    else:
        append_col_to_spreadsheet(token, SPREADSHEET_ID, ARKUSZ_LISTA_OBECNOŚCI, date_from_client)

    response = add_attendance_bool_rows(access_token=token,
                                        spreadsheet_id=SPREADSHEET_ID,
                                        sheet_name=ARKUSZ_LISTA_OBECNOŚCI,
                                        date_from_client=date_from_client,
                                        json_data=attendance_data)
    # ZMienic tutaj
    if not response['success']:
        return pretty_json_response(response, 400)

    return pretty_json_response(response)


@app.route('/columns', methods=['GET'])
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
@fetch_valid_token
def add_student(token):
    new_student_data = request.get_json()

    if not new_student_data:
        return pretty_json_response({'success': False, 'message': 'No data was sent'}, 400)

    retrieve_students = read_spreadsheet_data(token, SPREADSHEET_ID, ARKUSZ_UCZNIOWIE)
    if retrieve_students['success']:
        col_names = retrieve_students['data'][0]
        append_data_response = append_row_to_spreadsheet(access_token=token,
                                                         col_names=col_names,
                                                         spreadsheet_id=SPREADSHEET_ID,
                                                         sheet_name=ARKUSZ_UCZNIOWIE,
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


