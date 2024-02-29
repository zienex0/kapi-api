import json
import os

from flask import Flask, jsonify, request
from flask_cors import CORS

from services.google.gmail_api import send_mail
from services.google.spreadsheet_api import read_spreadsheet_data, read_spreadsheet_columns, append_row_to_spreadsheet
from services.google.get_google_token import get_google_token

from flask import Response

from dotenv import load_dotenv
load_dotenv()


app = Flask(__name__)
CORS(app)

GOOGLE_SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/gmail.send"]
SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')


def pretty_json(data, status_code):
    response = Response(response=json.dumps(data, indent=4, separators=(',', ': ')),
                        status=status_code,
                        mimetype="application/json")
    return response


@app.route('/')
def home():
    test_message = {'testing': 'it works', 'another test': 'it works'}
    return pretty_json(test_message, 200)


@app.route('/students_data', methods=['GET'])
def students_data():
    creds = get_google_token(scopes=GOOGLE_SCOPES)
    spreadsheet_response = read_spreadsheet_data(creds=creds, 
                                             spreadsheet_id=SPREADSHEET_ID, 
                                             range_name="Arkusz1")
    if spreadsheet_response["success"]:
        data = spreadsheet_response["data"]
        return pretty_json(data, 200)
    
    elif not spreadsheet_response["success"]:
        return pretty_json(spreadsheet_response, 400)

# TODO 1: Create the read_student_groups func to return it to the frontend
# @app.route('/student_groups', methods=['GET'])
# def student_groups():
#     pass


@app.route('/add_student', methods=['POST'])
def add_student():
    new_student_data = request.json
    
    creds = get_google_token(GOOGLE_SCOPES)
    columns_response = read_spreadsheet_columns(creds=creds, spreadsheet_id=SPREADSHEET_ID, range_name="Arkusz1")
    if columns_response["success"]:
        spreadsheet_columns = columns_response["data"]
        # Convert both to sets for comparison
        json_keys = set(new_student_data.keys())
        spreadsheet_keys = set(spreadsheet_columns)

        if json_keys != spreadsheet_keys:
            missing_keys = spreadsheet_keys - json_keys
            extra_keys = json_keys - spreadsheet_keys
            message = {"success": False, "message": "Column mismatch", "missing_keys": list(missing_keys), "extra_keys": list(extra_keys)}
            return pretty_json(message, 400)

        response = append_row_to_spreadsheet(creds=creds, 
                                            spreadsheet_id=SPREADSHEET_ID,
                                            range_name="Arkusz1",
                                            json_data=new_student_data)
        if response["success"]:
            mail_body = new_student_data

            send_mail(creds=creds, 
                        to=["wojtop@interia.pl", "szymon.zienkiewicz5@gmail.com"],
                        from_email="szymon.zienkiewicz5@gmail.com",
                        subject="Automatyczny mail po dostaniu formularza",
                        body=f"Ten mail został wysłany automatycznie, nie odpisuj na niego.\nOtrzymaliśmy nowy wypełniony formularz, zarejestrował się nowy uczestnik\n{mail_body}")
            message = {"message": "Row added to the spreadsheet successfuly. Mail automaticaly sent"}
            return pretty_json(message, 200)
        
        elif not response["success"]:
            return pretty_json(response, 400)
    
    else:
        message = {"success": False, "message": "Error while reading spreadsheet columns."}
        return pretty_json(message, 400)


def col_types_names():
    """
    Temporary function. Right now it is hardcoded.
    In the future, the customer will decide column types to make training forms correct 
    thus making editing correct.
    """
    
    types_names = {
    "Adres": "Adress",
    "Grupa": "Group",
    "Imię": "Name",
    "Jednorazowy trening": "OneTimer",
    "Kod pocztowy": "PostalCode",
    "Mail": "Mail",
    "Nazwisko": "Surname",
    "Rocznik": "Year",
    "Rozmiar koszulki": "Size",
    "Telefon": "Phone",
    "Uwagi": "Comments",
    "Zgoda na regulamin": "Agree"
    }
    
    return types_names


@app.route("/spreadsheet_col_names", methods=["GET"])
def column_names():
    creds = get_google_token(GOOGLE_SCOPES)

    column_names_response = read_spreadsheet_columns(creds=creds,
                                        spreadsheet_id=SPREADSHEET_ID,
                                        range_name="Arkusz1")
    if column_names_response["success"]:
        # col_names = column_names_response["data"]
        data_about_cols = col_types_names()
        return pretty_json(data_about_cols, 200)
    
    elif not column_names_response["success"]:
        return pretty_json(column_names_response, 400)


# TODO 2: Create edit_students_data func
# @app.route('/edit_student_data', methods=['PATCH'])
# def edit_student_data():
#     pass

# TODO 3: Send mail to the parent

if __name__ == '__main__':
    app.run()
