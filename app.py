from datetime import date
import firebase_admin
from openai import OpenAI
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import yaml
import requests
from models import User
import firebase_admin
from firebase_admin import credentials, auth, firestore
import secrets

app = Flask(__name__)
firebase = firebase_admin.initialize_app()
db = firestore.client()

with open('auth.yaml', 'r') as file:
    authfile = yaml.safe_load(file)

secret_key = authfile['flask']['secretKey']

firebase_config = authfile.get('firebase', {})

#Suhas nga replace this path with ur own path once I send you the json file, dont keep it in project folder for security reasons
cred = credentials.Certificate("/Users/rajaselvamjayakumar/Downloads/tsa-agriculture-app-firebase-adminsdk-4jash-f87e772be9.json")
app = firebase_admin.initialize_app(cred)
db = firestore.client()

api_usage = {
    'stormglass': 0,
    'weatherapi': 0,
    'date': str(date.today())  
}

def check_and_increment_usage(api_name):
    today_str = str(date.today())

    if api_usage['date'] != today_str:
        api_usage['stormglass'] = 0
        api_usage['weatherapi'] = 0
        api_usage['date'] = today_str

    if api_usage[api_name] >= 10:
        raise Exception(f"{api_name} daily request limit reached (10 requests).")


    api_usage[api_name] += 1



def get_stormglass_api():

    stormglass_response = requests.get(
        'https://api.stormglass.io/v2/bio/point',
        params={
            'lat': 58.7984,
            'lng': 17.8081,
            'params': ','.join(['soilMoisture','soilTemperature'])
        },
        headers={
            'Authorization': authfile['stormglass']['apiKey']
        }
    )
    response = stormglass_response.json()

    return response


def get_weatherapi_averages():
    
    weatherapi_response = requests.get(
        'https://api.weatherapi.com/v1/forecast.json',
        params={
            'key': authfile['weatherapi']['apiKey'],
            'q': 'Atlanta',
            'days': 10
        }
    )
    weather_data = weatherapi_response.json()  
    
    forecast_days = weather_data['forecast']['forecastday']
    daily_averages = []

    for day in forecast_days:
        date_str = day['date']
        hours = day['hour']

        total_temp = 0.0
        total_cloud = 0.0
        total_precip = 0.0
        count = 0

        for hour_data in hours:
            total_temp += hour_data['temp_c']
            total_cloud += hour_data['cloud']
            total_precip += hour_data['precip_in']
            count += 1

        avg_temp = round(total_temp / count, 2)
        avg_cloud = round(total_cloud / count, 2)
        avg_precip = round(total_precip / count, 2)

        daily_averages.append({
            "date": date_str,
            "averageTemperature": avg_temp,
            "averageCloud": avg_cloud,
            "averagePrecip": avg_precip
        })

    return {"daily_averages": daily_averages}

def chatbot_request(question):
    print(question)
    client = OpenAI(api_key=authfile['openAI']['apiKey'])
    instructions =  """
        You are AgriBot, an AI chatbot designed to serve only as an agricultural assistant. You can provide expert answers, guidance, and data related to agriculture, including:

        1. Crop Data: planting times, yield information, recommended seed varieties, soil nutrient needs, pest/disease management, harvesting guidelines, etc.
        2. Farming Practices: irrigation methods, sustainable farming, organic practices, use of pesticides and fertilizers, crop rotation, etc.
        3. Agricultural Economics: market trends, cost-benefit analysis of certain crops, yield projections, and similar topics.
        4. Agri-Tech: modern technologies like drones, sensors, or software solutions that help optimize crop production and farm management.

        Your only goal is to address questions in these agricultural domains. Ensure responses are 50 words or less and do not include markdown.
        """


    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": instructions},
            {
                "role": "user",
                "content": question
            }
        ]
    )
    response = dict(completion.choices[0].message)
    response = response['content']
    return response


def api_to_db():
    doc_id = str(date.today())

    stormglass_doc = db.collection("stormglass_data").document(doc_id).get()
    if not stormglass_doc.exists:
        stormglass_data = get_stormglass_api()  
        db.collection("stormglass_data").document(doc_id).set(stormglass_data)

    weatherapi_doc = db.collection("weatherapi_data").document(doc_id).get()
    if not weatherapi_doc.exists:
        weather_data = get_weatherapi_averages()  
        db.collection("weatherapi_data").document(doc_id).set(weather_data)

api_to_db()  
    

@app.route('/')
def index():
    if "currentUser" in session:
        username = session["currentUser"]['name']
    else:
        return redirect(url_for("signup"))
    
    doc_id = str(date.today())
    try:
        daily_averages = db.collection("weatherapi_data").document(doc_id).get().to_dict()
        stormglass_data = db.collection("stormglass_data").document(doc_id).get().to_dict()
        soil_moisture = stormglass_data['hours'][1]['soilMoisture']['noaa']
        soil_temperature = stormglass_data['hours'][1]['soilTemperature']['noaa']
    
        return render_template('dashboard.html', daily_averages=daily_averages['daily_averages'], soil_moisture=soil_moisture, soil_temperature=soil_temperature, username=username)
    except Exception as e:
        return f"Error: {str(e)}", 500


@app.route('/chatbot', methods=['GET'])
def chatbot_page():
    return render_template('chatbot.html')

@app.route('/chatbot', methods=['POST'])
def chatbot_api():
    data = request.get_json() 
    question = data.get('question', '')
    if not question.strip():
        return jsonify({'response': 'Please ask a question!'})

    bot_answer = chatbot_request(question)

    # Return JSON
    return jsonify({'response': bot_answer})


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
