import requests
import os
import random
import time
import json
from paho.mqtt import client as mqtt_client
import datetime

MQTT_USERNAME = os.getenv('BROKER_USERNAME')
MQTT_PASSWORD = os.getenv('BROKER_PASSWORD')
GLASS_USERNAME = os.getenv('GLASS_USERNAME')
GLASS_PASSWORD = os.getenv('GLASS_PASSWORD')
DIRECTORY_ID = "951cffa7-863f-4ae7-8f7e-ed682e690f91"
APPLICATION_ID = "3c85d8bb-5cc7-4f17-a68b-8c52a90a6634"
MQTT_BROKER = os.getenv('BROKER','mqtt')
MQTT_PORT = int(os.getenv('BROKER_PORT',1883))
TOPIC = "glass/mqtt"
GLASS_HOST="api.vitalenergiglass.co.uk"
glass_token=""
MQTT_CLIENT_ID = f'glass-mqtt-{random.randint(0, 1000)}'
FIRST_RECONNECT_DELAY = 1
RECONNECT_RATE = 2
MAX_RECONNECT_DELAY = 60

def connect_mqtt(client_id,broker,port,username,password):
    def on_connect(client, userdata, flags, rc):
    # For paho-mqtt 2.0.0, you need to add the properties parameter.
    # def on_connect(client, userdata, flags, rc, properties):
        if rc == 0:
            logger("Connected to MQTT Broker!")
        else:
            logger("Failed to connect, return code %d\n", rc)
    # Set Connecting Client ID
    client = mqtt_client.Client(client_id)

    # For paho-mqtt 2.0.0, you need to set callback_api_version.
    # client = mqtt_client.Client(client_id=client_id, callback_api_version=mqtt_client.CallbackAPIVersion.VERSION2)

    client.username_pw_set(username, password)
    client.on_connect = on_connect
    client.connect(broker, port)
    return client

def on_disconnect(client, userdata, rc):
    logger(f"Disconnected with result code: {rc}")
    reconnect_count, reconnect_delay = 0, FIRST_RECONNECT_DELAY
    while True:
        logger(f"Reconnecting in {reconnect_delay} seconds...")
        time.sleep(reconnect_delay)

        try:
            client.reconnect()
            logger("Reconnected successfully!")
            return
        except Exception as err:
            logger("{err}. Reconnect failed. Retrying...")

        reconnect_delay *= RECONNECT_RATE
        reconnect_delay = min(reconnect_delay, MAX_RECONNECT_DELAY)
        reconnect_count += 1

def publish(client,TOPIC,msg):
  status=1
  retries=1
  while status!=0 and retries<4:
    result = client.publish(TOPIC, msg)
    # result: [0, 1]
    status = result[0]
    if status != 0:
        logger(f"Attempt {retries}: Failed to send message to TOPIC {TOPIC}")
        retries+=1
    else:
        logger(f"Published {msg} to {TOPIC}")

def logger(message):
  print(f"{datetime.datetime.now().isoformat()}: {message}")

def glass_get(host,path,token):
	url=f"https://{host}{path}"
	headers={
		"Token": token,
		"Applicationid": APPLICATION_ID,
		"Content-Type": "application/json"
	}
	response=requests.get(url, headers=headers)
	return response

def glass_post(host,path,data):
	url=f"https://{host}{path}"
	headers={
		"Content-Type": "application/json",
		"Accept": "application/json, text/plain, */*",
		"Priority": "u=1, i",
		"Applicationid": APPLICATION_ID
	}
	response=requests.post(url, headers=headers, json=data)
	return response

def glass_check_token(token):
	response=glass_get(GLASS_HOST,"/api/v0-1/auth/",token)
	if response.status_code == 200:
		return response.json()["valid"]
	else:
		return false

def glass_get_resources(token):
	response=glass_get(GLASS_HOST,"/api/v0-1/virtualentity/",glass_token)
	resources={}
	if response.status_code == 200:
		for resource in response.json()[0]["resources"]:
			if resource["name"].lower()=="heat energy":
				resources["heat energy"]=resource["resourceId"]
			elif resource["name"].lower()=="heat energy cost":
				resources["heat energy cost"]=resource["resourceId"]
	else:
		logger(f"Could not get resources: {response.status_code}")
	return resources

def glass_get_kWh(resources,token):
	path=f'/api/v0-1/resource/{resources["heat energy"]}/meterread'
	response=glass_get(GLASS_HOST,path,token)
	if response.status_code == 200:
		if len(response.json()["data"])>0 and len(response.json()["data"][0])>1:
			return response.json()["data"][0][1]
		else:
			return -1
	else:
		logger(f"Could not get kWh value: {response.status_code}")
		return -1

def glass_get_cost_today(resources,token):
	today=datetime.datetime.today().strftime('%Y-%m-%d')
	path=f'/api/v0-1/resource/{resources["heat energy cost"]}/readings?from={today}T00:00:00&to={today}T23:59:59&period=P1D&function=sum'
	response=glass_get(GLASS_HOST,path,token)
	if response.status_code == 200:
		if len(response.json()["data"])>0 and len(response.json()["data"][0])>1:
			return response.json()["data"][0][1]
		else:
			return -1
	else:
		logger(f"Could not get cost value: {response.status_code}")
		return -1

def glass_get_kWh_today(resources,token):
	today=datetime.datetime.today().strftime('%Y-%m-%d')
	path=f'/api/v0-1/resource/{resources["heat energy"]}/readings?from={today}T00:00:00&to={today}T23:59:59&period=P1D&function=sum'
	response=glass_get(GLASS_HOST,path,token)
	if response.status_code == 200:
		if len(response.json()["data"])>0 and len(response.json()["data"][0])>1:
			return response.json()["data"][0][1]
		else:
			return -1
	else:
		logger(f"Could not get cost value: {response.status_code}")
		return -1

def glass_login():
	login={
		"username": GLASS_USERNAME,
		"password": GLASS_PASSWORD,
		"directoryId": DIRECTORY_ID
	}
	response=glass_post(GLASS_HOST,"/api/v0-1/auth/",login)
	if response.status_code == 200:
		if not response.json()["valid"]:
			logger(f"Login not accepted - please check credentials: {response.json()}")
			return ""
		else:
			return response.json()["token"]
	else:
		logger(f"Could not log in to glass: {response.status_code}")

def create_glass(client):
	device={
		"dev": {
			"ids": "glass_0001",
			"name": "glass",
			"mf": "Vital Energi",
			"mdl": "",
			"sw": "",
			"hw": "",
			"sn": "1234"
			},
		"o": {
			"name": "Vital Energi",
			"sw": "0.1",
			"url": f"https://{GLASS_HOST}"
		},
		"cmps": {
			"kWh": {
				"p": "sensor",
				"name":"kWh",
				"device_class":"energy",
				"state_class": "TOTAL_INCREASING",
				"unit_of_measurement":"kWh",
				"value_template":"{{ value_json.kwh | float }}",
				"unique_id": "glass_kwh"
			},
			"cost today":{
				"p": "sensor",
				"name":"Cost Today",
				"state_class": "TOTAL_INCREASING",
				"unit_of_measurement":"GBP",
				"value_template":"{{ value_json.cost_today |float }}",
				"unique_id": "glass_cost_today"
			},
			"usage today":
			{
				"p": "sensor",
				"name":"kWh_today",
				"state_class": "TOTAL_INCREASING",
				"device_class":"energy",
				"unit_of_measurement":"kWh",
				"value_template":"{{ value_json.kwh_today | float }}",
				"unique_id": "glass_kwh_today"
			}
		},
		"state_topic": TOPIC+"/state",
		"qos":2
	}
	publish(client, "homeassistant/device/glass/config", json.dumps(device).encode("utf-8"))


client=connect_mqtt(MQTT_CLIENT_ID,MQTT_BROKER,MQTT_PORT,MQTT_USERNAME,MQTT_PASSWORD)
client.on_disconnect = on_disconnect

while(1):
	create_glass(client)
	if not glass_check_token(glass_token):
		logger("Token invalid - will try to get a new one")
		glass_token=glass_login()
	resources=glass_get_resources(glass_token)
	kWh=glass_get_kWh(resources,glass_token)
	logger(f"kWh: {kWh}")
	kWh_today=glass_get_kWh_today(resources,glass_token)
	logger(f"kWh today: {kWh_today}")
	cost=glass_get_cost_today(resources,glass_token)/100
	logger(f"Cost: {cost}")
	if cost>=0 and kWh >=0 and kWh_today>=0:
		state={
			"kwh": kWh,
			"kwh_today": kWh_today,
			"cost_today": cost
		}
		publish(client,TOPIC+"/state",json.dumps(state).encode("utf-8"))
	time.sleep(295)
	publish(client,TOPIC+"/ping",f'{{"ping": "{datetime.datetime.now().isoformat()}"}}')
	time.sleep(5)




