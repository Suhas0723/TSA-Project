from datetime import date
import firebase_admin
from openai import OpenAI
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import yaml
import requests
import firebase_admin
from firebase_admin import credentials,  firestore
from geopy.geocoders import Nominatim
import json

app = Flask(__name__)

loc = Nominatim(user_agent="Geopy Library")

with open('auth.yaml', 'r') as file:
    authfile = yaml.safe_load(file)

app.secret_key = authfile['flask']['secretKey']

firebase_config = authfile.get('firebase', {})




cred = credentials.Certificate("tsa-agriculture-app-firebase-adminsdk-4jash-f87e772be9.json")
firebase = firebase_admin.initialize_app(cred)
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
    
    user = db.collection("users").document(session['currentUser']['uid']).get().to_dict()
    print(user, session['currentUser']['uid'])
    address = {
        "street": user['address']['line1'],
        "city": user['address']['city'],
        "state": user['address']['state'],
        "postalcode": user['address']['zip'],
        "country": user['address']['country'],
    }
    location = loc.geocode(address)

    try:
        lat = location.latitude
        lng = location.longitude
    except:
        lat = 33.7501
        lng = 84.3885

    stormglass_response = requests.get(
        'https://api.stormglass.io/v2/bio/point',
        params={
            'lat': lat,
            'lng': lng,
            'params': ','.join(['soilMoisture','soilTemperature'])
        },
        headers={
            'Authorization': authfile['stormglass']['apiKey']
        }
    )
    response = stormglass_response.json()

    return response

def get_weatherapi_averages():
    user = db.collection("users").document(session['currentUser']['uid']).get().to_dict()
    city = user['address']['city']

    weatherapi_response = requests.get(
        'https://api.weatherapi.com/v1/forecast.json',
        params={
            'key': authfile['weatherapi']['apiKey'],
            'q': city,
            'days': 3
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
            "averagePrecip": avg_precip, 
            "UV": weather_data['forecast']['forecastday'][0]['day']['uv']
        })

    return {"daily_averages": daily_averages}

def chatbot_request(question):
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

def get_plant(plant_id):
    base_url = f"https://trefle.io/api/v1/plants/{plant_id}"
    headers = {
        "Authorization": f"Bearer {authfile['plantApi']['apiKey']}"
    }
    try:
        response = requests.get(base_url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}


def plant_to_db(plant_data, uid):
    try:
        plant_data = dict(plant_data)

        print("Plant Data Received:", plant_data)

        data_section = plant_data.get("data", {})
        if not isinstance(data_section, dict):
            raise ValueError("The 'data' field is missing or not a dictionary.")
        
        slug = data_section.get("slug")
        if not slug or not isinstance(slug, str):
            raise ValueError("The 'slug' field is missing, empty, or not a string in the 'data' section.")

        if not uid or not isinstance(uid, str):
            raise ValueError("The 'uid' is missing, empty, or not a string.")

        doc_name = f"{slug}-{uid}"

        print(f"Slug: {slug}, UID: {uid}, Document Name: {doc_name}")

        db.collection('plant_data').document(doc_name).set(plant_data)
        print("Data successfully stored in Firestore.")

    except Exception as e:
        print(f"Error in plant_to_db: {e}")
        raise

def api_to_db(uid):
    doc_id = str(date.today())

    stormglass_doc = db.collection("stormglass_data").document(doc_id+"-"+uid).get()
    if not stormglass_doc.exists:
        stormglass_data = get_stormglass_api()
        print(stormglass_data)
        db.collection("stormglass_data").document(doc_id+"-"+uid).set(stormglass_data)
        

    weatherapi_doc = db.collection("weatherapi_data").document(doc_id+"-"+uid).get()
    if not weatherapi_doc.exists:
        weather_data = get_weatherapi_averages()  
        db.collection("weatherapi_data").document(doc_id+"-"+uid).set(weather_data)

@app.route('/')
def index():
    if "currentUser" in session:
        username = session["currentUser"]['name']
    else:
        return redirect(url_for("signup"))
    
    doc_id = str(date.today())
    try:
        uid = session['currentUser']['uid']
        collection_ref = db.collection('plant_data')
        documents = collection_ref.list_documents()
        matching_docs = []
        for doc in documents:
            doc_name = doc.id
            if uid in doc_name:
                matching_docs.append(doc.get().to_dict())

        if len(matching_docs) > 4:
            matching_docs = matching_docs[:4]
        daily_averages = db.collection("weatherapi_data").document(doc_id+"-"+session['currentUser']['uid']).get().to_dict()
        stormglass_data = db.collection("stormglass_data").document(doc_id+"-"+session['currentUser']['uid']).get().to_dict()
        soil_moisture = stormglass_data['hours'][1]['soilMoisture']['noaa']
        soil_temperature = stormglass_data['hours'][1]['soilTemperature']['noaa']

    
        return render_template('dashboard.html', plants = matching_docs, daily_averages=daily_averages['daily_averages'], soil_moisture=soil_moisture, soil_temperature=soil_temperature, username=username)
    except Exception as e:
        return f"Error: {str(e)}", 500

@app.route('/water-usage')
def water_usage():
    return render_template('water_usage1.html', uid=session['currentUser']['uid'], username=session['currentUser']['name'])


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

    return jsonify({'response': bot_answer})

@app.route('/api/create_user', methods=['POST'])
def create_user():
    data = request.json
    if not data:
        return jsonify({"message": "No data provided"}), 400

    uid = data.get('uid')
    user_data = data.copy()
    user_data[uid] = uid
    db.collection('users').document(uid).set(user_data)
    session['currentUser'] = user_data
    api_to_db(uid)
    return jsonify({"message": "User created successfully"}), 201

@app.route("/signup", methods=["GET"])
def signup():
    if request.method == "GET":
        return render_template("login_signup.html", firebase_config=firebase_config)
        
@app.route('/api/login_user', methods=['POST'])
def login_user():
    data = request.json
    if not data:
        return jsonify({"message": "No data provided"}), 400

    uid = data.get('uid')
    user_data = db.collection('users').document(uid).get().to_dict()
    user_data['uid'] = uid
    session['currentUser'] = user_data
    api_to_db(uid)
    return jsonify({"message": "API to DB process completed!"}), 200

@app.route('/logout')
def logout():
    session.pop('currentUser', None)
    return redirect(url_for('signup'))

@app.route('/crops/show-crops', methods=['GET'])
def crops_page():
    uid = session['currentUser']['uid']
    collection_ref = db.collection('plant_data')
    documents = collection_ref.list_documents()
    matching_docs = []
    for doc in documents:
        doc_name = doc.id
        if uid in doc_name:
            matching_docs.append(doc.get().to_dict())
    return render_template('crops.html', matching_docs=matching_docs)

@app.route('/crops', methods=['POST'])
def crops_api():
    try:
        plant_name = request.form['plant_name']
        if not plant_name.strip():
            error_message = "Plant name cannot be empty."
            return render_template("crops.html", error=error_message)

        plant_id = plant_name.lower().replace(' ', '-')

        name = plant_id+"-"+session['currentUser']['uid']
        for doc in db.collection('plant_data').list_documents():
            if name == doc.id:
                error_message = f"Plant: {plant_name} already exists in the database."
                return render_template("crops.html", error=error_message)

        plant_data = get_plant(plant_id)

        if 'error' in plant_data or 'data' not in plant_data:
            error_message = f"Could not fetch data for plant: {plant_name}"
            return render_template("crops.html", error=error_message)
        
        data = plant_data['data']
        extracted_data = {
            "common_name": data.get("common_name", "Unknown"),
            "scientific_name": data.get("scientific_name", "Unknown"),
            "image_url": data.get("image_url", ""),
            "slug": data.get("slug", ""),
            "uid": session['currentUser']['uid'],  
        }

        client = OpenAI(api_key=authfile['openAI']['apiKey'])
        instructions = "I will provide a plant's scientific name and you are to provide a brief description of the plant along with some basic care tips in under 50 words."
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": instructions},
                {
                    "role": "user",
                    "content": extracted_data['scientific_name']
                }
            ]
        )
        response = dict(completion.choices[0].message)
        response = response['content']
        extracted_data['description'] = response
        doc_name = f"{extracted_data['slug']}-{extracted_data['uid']}"

        db.collection('plant_data').document(doc_name).set(extracted_data)

        return redirect(url_for('crops_page'))

    except Exception as e:
        print(f"Error in crops_api: {e}")
        return jsonify({"error": str(e)}), 500
    
@app.route('/api/add_irrigation', methods=['POST'])
def add_irrigation():
    data = request.json
    if not data:
        return jsonify({"message": "No data provided"}), 400
    
    try:
        for_plant_slug = data['forPlant']

        uid = session['currentUser']['uid']
        collection_ref = db.collection('plant_data')
        documents = collection_ref.list_documents()

        matching_docs = []
        for doc in documents:
            doc_name = doc.id
            print("Checking document:", doc_name)
            if uid in doc_name:
                matching_docs.append(doc)

        plant_ref = None

        for doc in matching_docs:
            doc_snapshot = doc.get()
            doc_data = doc_snapshot.to_dict()
            if doc_data and doc_data.get('slug') == for_plant_slug:
                plant_ref = doc
                break

        if not plant_ref:
            return jsonify({"message": "Matching plant not found"}), 404

        plant_ref.update({
            'irrigations': firestore.ArrayUnion([data])
        })
        return jsonify({"message": "Irrigation added successfully"}), 201

    except Exception as e:
        print("no gotead", str(e))
        return jsonify({"message": f"An error occurred: {str(e)}"}), 500

@app.route('/api/get_crop_data', methods=['GET'])
def get_crop_data():
    try:

        uid = session['currentUser']['uid']
        collection_ref = db.collection('plant_data')
        documents = collection_ref.list_documents()
        matching_docs = []
        for doc in documents:
            doc_name = doc.id
            if uid in doc_name:
                matching_docs.append(doc.get().to_dict())
        print(matching_docs)

        print(matching_docs)
        return jsonify(matching_docs), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/update_crop_data', methods=['POST'])
def update_crop_data():
    data = request.json
    if not data or 'slug' not in data:
        return jsonify({"message": "Invalid data"}), 400

    slug = data['slug']
    water_cost = data['waterCost']
    field_area = data['fieldArea']
    crop_density = data['cropDensity']

    plant_ref = findPlantWithSlug(slug)

    if not plant_ref:
        return jsonify({"message": "Plant not found"}), 404


    plant_ref.update({
        'fieldArea': field_area,
        'cropDensity': crop_density,
        'waterCost' : water_cost
    })

    return jsonify({"message": "Crop data updated successfully"}), 200

def findPlantWithSlug(slug):
    uid = session['currentUser']['uid']
    collection_ref = db.collection('plant_data')
    documents = collection_ref.list_documents()

    matching_docs = []

    for doc in documents:
        doc_name = doc.id
        print("Checking document:", doc_name)
        if uid in doc_name:
            matching_docs.append(doc)

    plant_ref = None


    for doc in matching_docs:
        doc_snapshot = doc.get() 
        doc_data = doc_snapshot.to_dict()  
        if doc_data and doc_data.get('slug') == slug:
            return doc
        
@app.route("/api/growing_conditions", methods=["POST"])
def growing_conditions():
    data = request.json
    if not data or 'plantName' not in data:
        return jsonify({"message": "Invalid data provided"}), 400

    plant_name = data['plantName']
    uid = session.get('currentUser', {}).get('uid')

    plant_doc_ref = db.collection('plant_data').document(f'{plant_name}-{uid}')
    plant_doc = plant_doc_ref.get()

    try:
        score = plant_doc.get('growth_score')
    except:
        score = None

    if score is None:
        api_id = f"{date.today()}-{uid}"

        stormglass_doc = db.collection('stormglass_data').document(api_id).get()
        weather_doc = db.collection('weatherapi_data').document(api_id).get()

        stormglass_data = stormglass_doc.to_dict() 
        hours_data = stormglass_data.get('hours', [{}])

        conditions = {
            'soilMoisture': hours_data[0].get('soilMoisture', {}).get('sg', 0.0),
            #'soilTemp': hours_data[0].get('soilTemperature', {}).get('sg', 0.0),
        }

        weather_data = weather_doc.to_dict()
        daily_averages = weather_data.get('daily_averages', [{}])

        conditions.update({
            'avgCloud': daily_averages[0].get('averageCloud', 0.0),
            'avgPrecip': daily_averages[0].get('averagePrecip', 0.0),
            'avgTemp': daily_averages[0].get('averageTemperature', 0.0),
        })

        client = OpenAI(api_key=authfile['openAI']['apiKey'])
        instructions = "I will provide today's current soil and weather conditions, as well as a plant name. You must determine how well the plant can grow under these conditions, and return a score from 0 to 100. Try to keep the score on the higher end, only give bad score if the conditions are very poor. Only return the score number value, no other text at all."
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": instructions},
                {"role": "user", "content": f"Plant: {plant_name}, Conditions: {json.dumps(conditions)}"}
            ]
        )
        response = dict(completion.choices[0].message)['content']
        score = float(response.strip())

        plant_doc_ref.set({
            'growth_score': score,
            'date': str(date.today())
        }, merge=True)

    return jsonify({"growth_score": score}), 200



if __name__ == "__main__":
    app.run(debug=True)
