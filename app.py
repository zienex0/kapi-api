import json
import os
import logging

from flask import Flask, request
from flask_cors import CORS

from services.google.gmail_api import send_email
from services.google.spreadsheet_api import read_spreadsheet_data, append_row_to_spreadsheet
from services.google.get_google_token import get_access_token

from flask import Response

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)
CORS(app)

SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')
STUDENTS_DATA_RANGE_NAME = 'Arkusz1'


def refresh_spreadsheet_data():
    global spreadsheet_data
    token = get_access_token()
    spreadsheet_response = read_spreadsheet_data(access_token=token, spreadsheet_id=SPREADSHEET_ID, range_name=STUDENTS_DATA_RANGE_NAME)

    status = spreadsheet_response
    if status['success']:
        spreadsheet_data = status['data']
    else:
        spreadsheet_data = []
    return status


def pretty_json(data, status_code):
    response = Response(response=json.dumps(data, indent=4, separators=(',', ': ')), status=status_code, mimetype="application/json")
    return response


spreadsheet_data = []

@app.route('/')
def home():
    test_message = {'testing': 'it works', 'another test': 'it works'}
    return pretty_json(test_message, 200)


@app.route('/refresh_spreadsheet')
def on_demand_refresh():
    refresh_spreadsheet_data()

    col_names = spreadsheet_data[0]
    list_of_json_values = []

    for row_indx in range(1, len(spreadsheet_data)):
        row = spreadsheet_data[row_indx]
        row_values = {col_names[i]:row[i] for i in range(len(col_names))}
        list_of_json_values.append(row_values)

    msg = {"success": True, "data": list_of_json_values}
    return pretty_json(msg["data"], 200)


@app.route('/students_data', methods=['GET'])
def students_data():
    if not spreadsheet_data:
        status = refresh_spreadsheet_data()
        if status["success"]:
            pass
        else:
            return pretty_json(status, 400)

    col_names = spreadsheet_data[0]
    list_of_json_values = []

    for row_indx in range(1, len(spreadsheet_data)):
        row = spreadsheet_data[row_indx]
        row_values = {col_names[i]:row[i] for i in range(len(col_names))}
        list_of_json_values.append(row_values)

    msg = {"success": True, "data": list_of_json_values}
    return pretty_json(msg["data"], 200)


@app.route('/student_groups', methods=['GET'])
def student_groups():
    if not spreadsheet_data:
        status = refresh_spreadsheet_data()
        if status["success"]:
            pass
        else:
            return pretty_json(status, 400)

    groups_col_name = "Grupa"
    col_name_index = spreadsheet_data[0].index(groups_col_name)
    unique_groups = set()

    for row in spreadsheet_data[1:]:
        group_name = row[col_name_index]
        if group_name.isdigit():
            unique_groups.add(int(group_name))
        else:
            unique_groups.add(group_name)

    unique_groups_list = list(unique_groups)
    unique_groups_list.sort()
    return pretty_json(unique_groups_list, 200)


@app.route('/students_by_group', methods=['GET'])
def students_by_group():
    if not spreadsheet_data:
        status = refresh_spreadsheet_data()
        if status["success"]:
            pass
        else:
            return pretty_json(status, 400)

    desired_group = request.args.get('group', default=None, type=int)
    if not desired_group:
        message = {"success": False, "message": "Group name is required as a query parameter"}
        return pretty_json(message, 400)

    desired_group = str(desired_group)

    groups_col_name = "Grupa"
    col_name_index = spreadsheet_data[0].index(groups_col_name)

    filtered_students = []
    for row in spreadsheet_data[1:]:
        if row[col_name_index] == desired_group:
            filtered_students.append(row)

    return pretty_json(filtered_students, 200)


@app.route('/add_student', methods=['POST'])
def add_student():
    new_student_data = request.json
    if not spreadsheet_data:
        status = refresh_spreadsheet_data()
        if status["success"]:
            pass
        else:
            return pretty_json(status, 400)


    spreadsheet_columns = spreadsheet_data[0]

    json_keys = set(new_student_data.keys())
    spreadsheet_keys = set(spreadsheet_columns)

    if json_keys != spreadsheet_keys:
        missing_keys = spreadsheet_keys - json_keys
        extra_keys = json_keys - spreadsheet_keys
        message = {"success": False, "message": "Column mismatch", "missing_keys": list(missing_keys), "extra_keys": list(extra_keys)}
        return pretty_json(message, 400)

    token = get_access_token()
    response = append_row_to_spreadsheet(access_token=token,
                                            col_names=spreadsheet_columns,
                                            spreadsheet_id=SPREADSHEET_ID,
                                            range_name=STUDENTS_DATA_RANGE_NAME,
                                            json_data=new_student_data)
    if response["success"]:
        mail_body = new_student_data
        token = get_access_token()
        response = send_email(access_token=token, 
                              sender='szymon.zienkiewicz5@gmail.com', 
                              to=["wojtop@interia.pl", "szymon.zienkiewicz5@gmail.com"],
                              subject='Automatyczny mail po dostaniu formularza',
                              message_text=f'Ten mail został wysłany automatycznie, nie odpisuj na niego.\nOtrzymaliśmy nowy wypełniony formularz, zarejestrował się nowy uczestnik\n{mail_body}')
        if response['success']:
            message = {"success": True, "message": "Row added to the spreadsheet successfuly. Mail automaticaly sent"}
            return pretty_json(message, 200)
        else:
            return pretty_json(response, 400)

    elif not response["success"]:
        return pretty_json(response, 400)


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

    return types_names


@app.route("/spreadsheet_col_names", methods=["GET"])
def column_names():
    if not spreadsheet_data:
        status = refresh_spreadsheet_data()
        if status["success"]:
            pass
        else:
            return pretty_json(status, 400)

    col_names = spreadsheet_data[0]
    data_about_cols = col_types_names()
    return pretty_json(data_about_cols, 200)


# TODO 2: Create edit_students_data func
# @app.route('/edit_student_data', methods=['PATCH'])
# def edit_student_data():
#     pass

# TODO 3: Send mail to the parent

if __name__ == '__main__':
    app.run()



