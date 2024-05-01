from flask import Flask, render_template, request, jsonify, abort, make_response
from db import init_user_db, init_db, init_key_db, insert_db, insert_user_db, request_db, query_apiauth_by_key, replace_key, query_user_db, query_user_email
from functools import wraps
from datetime import datetime, timedelta
from keygen import gen_api_key
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import secrets
import json
import jwt
import uuid
import sys
import os
import re

app = Flask(__name__)

#get env var for jwt secret key
load_dotenv()
secret_key = os.environ['JWT_SECRET_KEY']

app.config['SECRET_KEY'] = secret_key

#database initializations
init_user_db()
init_db()
init_key_db()

global_password = None

#wrapper function, requires jwt token before request is authorized
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        print("args: ", args)
        print("f: ",f)
        print("This request needs a token, has headers: ",request.headers)
        #jwt is passed in the request header
        if 'x-access-token' in request.headers:
            token = request.headers['x-access-token']
            print("There is a token: ", token)
        #return 401 if token is not passed
        if not token:
            return jsonify({'message' : 'Token is missing !!'}), 401

        try:
            #decoding the payload to fetch the stored details
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms="HS256")
            current_user = query_user_db(data['public_id'])
        except Exception as e:
            return jsonify({
                'message' : 'Token is invalid !!'
            }), 401
        #returns the current logged in users context to the routes
        return f(current_user, *args, **kwargs)

    return decorated

# wrapper function, check for valid username, email, password during signup
def valid_signup(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        name, email = request.json['name'], request.json['email']
        password = request.json['password']
        print(f"Name: {name}, Email: {email}, Password: {password}")
        # username must not be nothing
        if (not len(name)):
            print("Name cannot be empty")
            return jsonify({'message' : 'Name cannot be empty'}), 422

        # valid email is something like 'user@email.com'
        email_regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'
        if (not re.fullmatch(email_regex, email)):
            print("Email format invalid")
            return jsonify({'message' : 'Invalid email'}), 422

        # password requirements:
        # at least 8 characters
        # at least 1 lowercase letter
        # at least 1 uppercase letter
        # at least 1 number
        # at least 1 special character from (_, -, @, $, !)
        # no whitespace
        valid_pw = True
        if (len(password) < 8):
            valid_pw = False
        elif (not re.search('[a-z]', password)):
            valid_pw = False
        elif (not re.search('[A-Z]', password)):
            valid_pw = False
        elif (not re.search('[0-9]', password)):
            valid_pw = False
        elif (not re.search('[_\-@$!]', password)):
            valid_pw = False
        elif (re.search('\s', password)):
            valid_pw = False

        if (not valid_pw):
            print("Invalid password format")
            return jsonify({'message' : 'Invalid password'}), 422

        return f(*args, **kwargs)

    return decorated

#default route, goes to underconstruction landing page
@app.route('/')
def index():
    return render_template('index.html')

#send-data route, used for hub to send data
#verifies key from hub and stores data into db
@app.route('/api/sensor-data', methods=['POST'])
def send_data():
    reiss = False
    api_key = request.json['api_key']
    query_resp = query_apiauth_by_key(api_key)
    if(query_resp[0] == False):
        data = {
            "Response": "Forbidden Gateway, You Do Not Have Access"
        }
        return data, 403

    session_id = request.json['session_id']
    sink_id = request.json['sink_id']
    sensor_id = request.json['sensor_id']
    water_amount = request.json['water_amount']
    duration = request.json['duration']
    start_time = request.json['start_time']
    end_time = request.json['end_time']
    date = request.json['date']
    is_error = request.json['is_error']

    insert_db('sessions', session_id, sink_id, sensor_id, water_amount, duration, start_time, end_time, date, is_error)

    if ((datetime.strptime(date, '%Y-%m-%d').date() - query_resp[1]) >= timedelta(days=7)):
        reiss = True

    if (reiss):
        new_key = gen_api_key()
        replace_key(api_key, new_key, date)

        data = {
            "api_key": new_key,
            "Response": "Successful"
        }
    else:
        data = {
            "Response": "Successful"
        }

    return data, 201

#receive-data route, sends data to phone given date
@app.route('/api/user-data', methods=['GET'])
@token_required
def receive_data():
    session_ids = []
    sink_ids = []
    sensor_ids = []
    water_amounts = []
    durations = []
    start_times = []
    end_times = []
    dates = []
    is_errors = []

    date = request.args.get('date')
    data = request_db(date)
    for i in range(len(data)):
        session_ids.append(str(data[i][0]))
        sink_ids.append(str(data[i][1]))
        sensor_ids.append(str(data[i][2]))
        water_amounts.append(str(data[i][3]))
        durations.append(str(data[i][4]))
        start_times.append(data[i][5].strftime("%H:%M:%S"))
        end_times.append(data[i][6].strftime("%H:%M:%S"))
        dates.append(data[i][7].strftime("%m/%d/%Y"))
        is_errors.append(str(data[i][8]))
    print(session_ids, sink_ids, sensor_ids, water_amounts, durations, start_times, end_times, dates, is_errors)
    data_packets = []
    for i in range(len(session_ids)):
        data_packet = {
            "session ID": session_ids[i],
            "sink ID": sink_ids[i],
            "sensor ID": sensor_ids[i],
            "water amount": water_amounts[i],
            "duration": durations[i],
            "start time": start_times[i],
            "end time": end_times[i],
            "date": dates[i],
            "is error": is_errors[i]
        }
        data_packets.append(data_packet)
    json_data = json.dumps(data_packets)

    return json_data, 200

@app.route('/api/iphone-test', methods=['GET'])
def iphone_test():
    return 'success, 2+2=5'

@app.route('/api/iphone-test-2', methods=['GET'])
@token_required
def iphone_test_2(self):
    data = {
            "Subject": "Iphone-Test",
            "Data": "12345"
    }
    return data, 200

@app.route('/login', methods=['POST'])
def login():
    #creates dictionary of form data
    
    if not request or not request.json['email'] or not request.json['password']:
        #returns 401 if any email or / and password is missing
        print("Could not verify, Login Required")
        return make_response(
            'Could not verify',
            401,
            {'WWW-Autheenticate' : 'Basic realm ="Login required!!"'}
        )

    user = query_user_email(request.json['email'])
    if not user:

        #returns 401 if user does not exist
        print("Could not verify, User does not exist")
        return make_response(
            'Could not verify',
            403,
            {'WWW-Authenticate' : 'Basic realm ="User does not exists !!"'}
        )
    if check_password_hash(user[3].strip(' '), request.json['password']):
        #generate the JWT Token
        token = jwt.encode({
            'public_id': user[0],
            'exp' : datetime.utcnow() + timedelta(weeks=1)
        }, app.config['SECRET_KEY'], algorithm="HS256")

        return make_response(jsonify({'token': token}), 201)
    #returns 403 if password is wrong
    return make_response(
        'Could not verify',
        401,
        {'WWW-Authenticate' : 'Basic realm ="Wrong Password !!"'}
    )

@app.route('/signup', methods=['POST'])
@valid_signup
def signup():
    
    #gets name, email and password
    name, email = request.json['name'], request.json['email']
    password = request.json['password']
    print(f"Name: {name}, email: {email}, password: {password}")
    if( name == None and email == None and password == None):
        print("Phone tried to send JSON but nothing was received")

    #checking for existing user
    user = query_user_email(email)
    if not user:
        password_hash = generate_password_hash(password)
        insert_user_db(str(uuid.uuid4()), name, email, password_hash)
        return make_response('Successfully registered.', 201)
    else:
        # returns 202 if user already exists
        return make_response('User already exists. Please Log in.', 202)

@app.route('/post-echo', methods=['POST'])
def post_echo():
    if request.is_json:
        json_data =  request.get_json()
        print(json_data)
        return jsonify(json_data)
    else:
        return jsonify({'error': 'Invalid JSON'}), 400

if __name__ == '__main__':
    # Specify the IP address here
    app.run()
