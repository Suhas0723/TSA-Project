from flask import Flask, render_template
import yaml
import requests

app = Flask(__name__)

with open('auth.yaml', 'r') as file:
    auth = yaml.safe_load(file)
	
stormglass_response = requests.get(
  'https://api.stormglass.io/v2/bio/point',
  params={
    'lat': 58.7984,
    'lng': 17.8081,
    'params': ','.join(['soilMoisture', 'soilTemperature'])
  },
  headers={
    'Authorization': auth['stormglass']['apiKey']
  }
)

stormglass_data = stormglass_response.json()

weatherapi_response = requests.get(
    'https://api.weatherapi.com/v1/forecast.json', 
    params={
        'key': auth['weatherapi']['apiKey'],
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
	return render_template("index.html")

if __name__ == "__main__":
	app.run(debug=True)
