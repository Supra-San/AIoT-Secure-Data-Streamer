import paho.mqtt.client as mqtt
import pandas as pd
import json
import os
import random
import logging
import sys
from dotenv import load_dotenv
from datetime import datetime

# ==========================================
# 1. CONFIGURATION (HEADER SECTION)
# ==========================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

# MQTT Configuration from .env
BROKER = os.getenv("MQTT_BROKER")
PORT = os.getenv("MQTT_PORT") # get port number from .env
TOPIC = os.getenv("MQTT_TOPIC")
MQTT_USER = os.getenv("MQTT_USER")
MQTT_PASS = os.getenv("MQTT_PASS")
CA_CERT_PATH = os.getenv("CA_CERT_PATH")
CLIENT_ID = os.getenv("MQTT_CLIENT_ID") or f"subscriber-{random.randint(1000, 9999)}"

# Data Storage Configuration
CSV_FILENAME = "sensor_data_room1.csv"
BUFFER_THRESHOLD = 5  # Number of readings before converting to dataframe

# Check if all required environment variables are set
if not all([BROKER, PORT, TOPIC, CA_CERT_PATH]):
    print("❌ Error: Missing required environment variables in .env file.")
    sys.exit(1)

PORT = int(PORT) # Convert to integer after ensuring it exists

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ==========================================
# 2. DATA PROCESSING LOGIC
# ==========================================
data_buffer = []

def on_message(client, userdata, msg):
    try:
        # 1. Decode payload
        raw_data = msg.payload.decode()
        payload = json.loads(raw_data)
        
        # 2. Schema Validation
        required_keys = ['temperature', 'humidity']
        if not all(key in payload for key in required_keys):
            print(f"⚠️ Validation Failed: Missing keys in payload: {payload}")
            return

        # 3. Data Integrity & Type Validation
        # Ensure values are numeric and not empty/None
        try:
            temp = float(payload['temperature'])
            humi = float(payload['humidity'])
        except (ValueError, TypeError):
            print(f"⚠️ Validation Failed: Non-numeric data received: {payload}")
            return

        # 4. Out-of-range Physical Check
        # Example: DHT22 sensor doesn't read temperature > 80°C or < -40°C
        if not (-40 <= temp <= 80) or not (0 <= humi <= 100):
            print(f"⚠️ Validation Failed: Sensor values out of physical range: {payload}")
            return

        # 5. Add timestamp if valid
        payload['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 6. Save to buffer
        data_buffer.append(payload)
        print(f"✅ Data Validated & Received: {payload} | Total: {len(data_buffer)}")

        # Data ingestion into Pandas every 5 data points
        if len(data_buffer) % 5 == 0:
            df = pd.DataFrame(data_buffer)
            # Interpolate missing data for numeric columns
            numeric_cols = ['temperature', 'humidity']
            df[numeric_cols] = df[numeric_cols].interpolate(method='linear').ffill().bfill()
            df.to_csv("sensor_data_room1.csv", index=False)
            
            # Print average temperature and humidity
            print(f"Average Temperature\t: {round(df['temperature'].mean(), 2)}°C")
            print(f"Average Humidity\t: {round(df['humidity'].mean(), 2)}%")
            print("--- [ LIVE PANDAS DATAFRAME UPDATED ] ---\n")

    except json.JSONDecodeError:
        print(f"❌ Error: Failed to decode JSON payload: {msg.payload}")
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")

        
# ==========================================
# 3. MQTT CLIENT SETUP & EXECUTION
# ==========================================
client = mqtt.Client(client_id=CLIENT_ID, callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
client.username_pw_set(MQTT_USER, MQTT_PASS)

# TLS Configuration
if os.path.exists(CA_CERT_PATH):
    client.tls_set(ca_certs=CA_CERT_PATH)
else:
    logging.error(f"CA Certificate not found at: {CA_CERT_PATH}")
    sys.exit(1)

client.on_message = on_message

try:
    logging.info(f"Connecting to {BROKER} on Port {PORT}...")
    client.connect(BROKER, PORT)
    client.subscribe(TOPIC)
    logging.info(f"Subscriber Active. Subscribed to topic: {TOPIC}")
    client.loop_forever()
except KeyboardInterrupt:
    logging.info("Disconnected by user. Saving final data...")
    if data_buffer:
        pd.DataFrame(data_buffer).to_csv(CSV_FILENAME, index=False)
    sys.exit(0)
except Exception as e:
    logging.error(f"Failed to connect: {e}")
