from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import yaml
import requests
from models import User
import firebase_admin
from firebase_admin import credentials, auth, firestore
import secrets

app = Flask(__name__)

with open('auth.yaml', 'r') as file:
    authfile = yaml.safe_load(file)

app.secret_key = authfile['flask']['secretKey']

firebase_config = authfile.get('firebase', {})

#Suhas nga replace this path with ur own path once I send you the json file, dont keep it in project folder for security reasons
cred = credentials.Certificate("/Users/rajaselvamjayakumar/Downloads/tsa-agriculture-app-firebase-adminsdk-4jash-f87e772be9.json")
firebase_admin.initialize_app(cred)

db = firestore.client()

stormglass_response = requests.get(
  'https://api.stormglass.io/v2/bio/point',
  params={
    'lat': 58.7984,
    'lng': 17.8081,
    'params': ','.join(['soilMoisture', 'soilTemperature'])
  },
  headers={
    'Authorization': authfile['stormglass']['apiKey']
  }
)

stormglass_data = stormglass_response.json()

weatherapi_response = requests.get(
    'https://api.weatherapi.com/v1/forecast.json', 
    params={
        'key': authfile['weatherapi']['apiKey'],
        'q': "Atlanta",
        'days': 10
    }
)

weatherapi_data = weatherapi_response.json()


average_temperatures = []
average_cloud_covers = []
average_precipitations = []

for day in weatherapi_data['forecast']['forecastday']:
    total_temp = 0
    total_cloud = 0
    total_precip = 0
    count = 0

    for hour in day['hour']:
        total_temp += hour['temp_c']
        total_cloud += hour['cloud']
        total_precip += hour['precip_in']
        count += 1

    avg_temp = round(total_temp / count)
    avg_cloud = round(total_cloud / count)
    avg_precip = round(total_precip / count)

    average_temperatures.append(avg_temp)
    average_cloud_covers.append(avg_cloud)
    average_precipitations.append(avg_precip)

@app.route("/")
def index():
    if "currentUser" in session:
        username = session["currentUser"]['name']
    else:
        return redirect(url_for("signup"))
    
    return render_template("index.html", username=username)

@app.route('/api/create_user', methods=['POST'])
def create_user():
    data = request.json
    if not data:
        return jsonify({"message": "No data provided"}), 400

    # Extract user details
    uid = data.get('uid')
    session['currentUser'] = db.collection('users').document(uid).get().to_dict()

    return jsonify({"message": "User created successfully"}), 201

@app.route("/signup", methods=["GET"])
def signup():
    if request.method == "GET":
        # Render the signup page
        return render_template("login_signup.html", firebase_config=firebase_config)
        
@app.route('/api/login_user', methods=['POST'])
def login_user():
    data = request.json
    if not data:
        return jsonify({"message": "No data provided"}), 400

    # Extract user details
    uid = data.get('uid')

    session['currentUser'] = db.collection('users').document(uid).get().to_dict()
    print(session['currentUser'])

    return jsonify({"message": "Login successful"}), 200

@app.route('/logout')
def logout():
    session.pop('currentUser', None)
    return redirect(url_for('signup'))

if __name__ == "__main__":
	app.run(debug=True)
