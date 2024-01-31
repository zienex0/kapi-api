import json
import os

from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy

from flask_cors import CORS

import bcrypt

import pandas as pd

from datetime import datetime


app = Flask(__name__)
instance_path = app.instance_path
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(instance_path, 'users.db')
db = SQLAlchemy(app)
CORS(app)


def generate_hash(password):
    password = password.encode('utf-8') 
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password, salt)
    return hashed


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String, unique=True, nullable=False)
    password_hash = db.Column(db.String, nullable=False)
    status = db.Column(db.String, nullable=False)
    payment_date = db.Column(db.DateTime)


    def check_password(self, password):
        password = password.encode('utf-8')
        return bcrypt.checkpw(password, self.password_hash)


@app.route('/')
def home():
    return jsonify({'testing': 'it works', 'another test': 'it works'})


@app.route('/students_data', methods=['GET'])
def students_data():
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(BASE_DIR, 'data', 'tmp_uczniowie_updated.xlsx')
    df = pd.read_excel(data_path)
    json_df = df.to_json(orient='records')
    parsed_json = json.loads(json_df)

    return jsonify(parsed_json)


@app.route('/student_groups', methods=['GET'])
def student_groups():
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(BASE_DIR, 'data', 'tmp_uczniowie_updated.xlsx')
    df = pd.read_excel(data_path)

    grupy = df['id_grupy'].value_counts().reset_index()
    grupy.columns = ['id_grupy', 'count']
    
    ilosc_grup = int(len(grupy['id_grupy']))
    lista_grup = grupy['id_grupy'].to_list()

    return jsonify({'ilosc_grup': ilosc_grup, 'lista_grup': lista_grup}), 200



@app.route('/add_student', methods=['POST'])
def add_student():
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(BASE_DIR, 'data', 'tmp_uczniowie_updated.xlsx')
    df = pd.read_excel(data_path)

    new_student_data = request.json

    try:
        new_student_data['data_urodzenia'] = datetime.strptime(new_student_data['data_urodzenia'], '%Y-%m-%d')
        new_student_data['data_dolaczenia'] = datetime.strptime(new_student_data['data_dolaczenia'], '%Y-%m-%d')
    except ValueError as e:
        return jsonify({'message': f'Error processing date: {e}'}), 400

    df = df.append(new_student_data, ignore_index=True)
    df.to_excel(data_path, index=False)    

    return jsonify({'message': 'User added successfully'}), 200


@app.route('/edit_student_data', methods=['PATCH'])
def edit_student_data():
    whole_student_data = request.json
    # {'id_ucznia': 1,
    #  'imie': 'Jan',
    #  'nazwisko': 'Kowalski',
    #  'data_urodzenia': 2005-01-01 # jako DateTime,
    #  'adres_ucznia': ul. Fasolowa,
    #  'telefon': '000-000-000',
    #  'email': 'user19@example.com',
    #  'id_grupy': 1,
    #  'data_dolaczenia': 2023-08-12 # jako DateTime,
    #  'poziom_umiejetnosci': 'Zaawansowany',
    #  'uwagi': 'cokolwiek'}

    id_ucznia = whole_student_data['id_ucznia']
    
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(BASE_DIR, 'data', 'tmp_uczniowie_updated.xlsx')
    df = pd.read_excel(data_path)

    student_to_edit = df[df['id_ucznia'] == id_ucznia].index

    if not student_to_edit.empty:
        for key, value in whole_student_data.items():
            df.at[student_to_edit, key] = value  # find the user in the table by its index and the column name
        
        df.to_excel(data_path, index=False)  # replace the file with new updated table

        return jsonify({'message': 'Student data updated successfully'}), 200
    else:
        return jsonify({'error': 'Student not found'}), 404


@app.route('/register_user', methods=['POST'])
def register_user():
    login = request.json['login']
    password = request.json['password']
    status = request.json['status']

    password_hash = generate_hash(password)

    new_user = User(login=login,
                    password_hash=password_hash,
                    status=status)    
    db.session.add(new_user)
    db.session.commit()

    return jsonify({'message': f'User with a new id of: {new_user.id} created successfully'}), 201



@app.route('/login_user', methods=['POST'])
def login_user():

    login = request.json['login']
    password = request.json['password']
    
    user = User.query.filter_by(login=login).first()
    if user:
        if user.check_password(password):
            return jsonify({'message': f'Login successful',
                            'user_status': user.status}), 200
        else:
            return jsonify({'message': f'Invalid password (hash: {generate_hash(password)})'}), 401
    else:
        return jsonify({'message': f'User with login: {login} was not found'}), 401
      
       
if __name__ == '__main__':
    app.run()