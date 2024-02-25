import json
import os

from flask import Flask, jsonify, request
from flask_cors import CORS

from services.google.gmail_api import send_mail
from services.google.spreadsheet_api import read_spreadsheet_data, read_spreadsheet_columns, append_row_to_spreadsheet
from services.google.get_google_token import get_google_token


app = Flask(__name__)
CORS(app)

GOOGLE_SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/gmail.send"]
SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')


@app.route('/')
def home():
    return jsonify({'testing': 'it works', 'another test': 'it works'})


@app.route('/students_data', methods=['GET'])
def students_data():
    creds = get_google_token(scopes=GOOGLE_SCOPES)
    spreadsheet_data_as_json = read_spreadsheet_data(creds=creds, 
                                                     spreadsheet_id=SPREADSHEET_ID, 
                                                     range_name="Arkusz1")
    
    return jsonify(spreadsheet_data_as_json), 200

# TODO 1: Create the read_student_groups func to return it to the frontend
# @app.route('/student_groups', methods=['GET'])
# def student_groups():
#     pass


@app.route('/add_student', methods=['POST'])
def add_student():
    new_student_data = request.json
    if len(new_student_data) != len(read_spreadsheet_columns()):
        return jsonify({"error": "The numbers of requested columns are not matching"}), 400
    
    creds = get_google_token(GOOGLE_SCOPES)
    try:
        success = append_row_to_spreadsheet(creds=creds, 
                                        spreadsheet_id=SPREADSHEET_ID,
                                        range_name="Arkusz1",
                                        json_data=new_student_data)
        if success:
            send_mail(creds=creds, 
                      to=["wojtop@interia.pl", "szymon.zienkiewicz5@gmail.com"],
                      from_email="szymon.zienkiewicz5@gmail.com",
                      subject="Automatyczny mail po dostaniu formularza",
                      body="Ten mail został wysłany automatycznie, nie odpisuj na niego.\nOtrzymaliśmy nowy wypełniony formularz, zarejestrował się nowy uczestnik")
            
            return jsonify({"message": "Row added to the spreadsheet successfuly. Mail automaticaly sent"}), 200
        else:
            return jsonify({"error": "Unexpected error occurred"}), 500
    except Exception as e:
        return jsonify({"error": e})
        

@app.route("/spreadsheet_col_names", methods=["GET"])
def column_names():
    creds = get_google_token(GOOGLE_SCOPES)
    try:
        col_names = read_spreadsheet_columns(creds=creds,
                                            spreadsheet_id=SPREADSHEET_ID,
                                            range_name="Arkusz1")
        if col_names:
            return jsonify(col_names), 200
        else:
            return jsonify({"message": "Unexpected error occurred"}), 500
    except Exception as e:
        return jsonify({"error": e})


# TODO 2: Create edit_students_data func
# @app.route('/edit_student_data', methods=['PATCH'])
# def edit_student_data():
#     pass

# TODO 3: Send mail to the parent

if __name__ == '__main__':
    app.run()