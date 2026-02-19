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
BUFFER_THRESHOLD = 5  # Setting number of data before convert to dataframe

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
        # Decode JSON payload
        payload = json.loads(msg.payload.decode())
        payload['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        data_buffer.append(payload)
        logging.info(f"📥 Data Received. Buffer Size: {len(data_buffer)}")

        # Convert to Dataframe & Save periodically
        if len(data_buffer) % BUFFER_THRESHOLD == 0:
            df = pd.DataFrame(data_buffer)
            print("\n" + "="*30)
            print(" [ LIVE PANDAS DATAFRAME ] ")
            print(df.tail(BUFFER_THRESHOLD))
            print(f"Average Temperature: {df['temperature'].mean():.2f}°C")
            print("="*30 + "\n")
            
            # Save to CSV (Atomic Action)
            df.to_csv(CSV_FILENAME, index=False)
            
    except Exception as e:
        logging.error(f"Error processing message: {e}")

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
