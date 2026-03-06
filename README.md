# Secure AIoT Data Stream: ESP32 to Pandas Pipeline 🚀
This project demonstrates a robust, end-to-end IoT data pipeline—from hardware sensing to real-time data engineering. It features a secure communication layer using TLS/SSL and processes live data into Pandas DataFrames for future AI-driven analysis.

The goal of this project is to stream environmental data (Temperature & Humidity) from an ESP32 microcontroller to a centralized Python environment securely. Unlike standard IoT tutorials, this project implements industry-standard security and real-time data ingestion.

# System Architecture :
* Edge: ESP32 + DHT22 Sensor.
* Security: Encrypted transmission via MQTTS (Port 8883) with CA Certificate validation.
* Broker: Eclipse Mosquitto with TLS configuration, password authentication, and ACL.
* Data Processor: Python Subscriber (`app_subscriber.py`) using Paho-MQTT & Pandas.
* Feature Engineering: Automated timestamping, data validation (range & schema), real-time linear interpolation for missing data, and live averaging.

# Folder Structure
After running `setup.sh`, your folder structure will be as follows:

        📁  AIoT-Secure-Data-Streamer
        ├── 📁 certs
        │   ├── 📄 ca.crt
        │   ├── 📄 server.crt
        │   └── 📄 server.key
        ├── 📁 config
        │   ├── ⚙️ mosquitto.conf
        │   ├── ⚙️ mosquitto.conf.example
        │   ├── 📄 passwd
        │   └── 📄 passwd.example
        ├── 📁 edge
        │   ├── 📄 esp32_publisher.ino
        │   ├── ⚡ secrets.h
        │   └── 📄 secrets.h.example
        ├── 📁 security
        │   ├── 📄 acl
        │   └── 📄 acl.example
        ├── 📁 pki
        │   ├── 📄 ca.key
        │   └── 📄 server.csr
        ├── 📝 README.md
        ├── 🐍 app_subscriber.py
        ├── 🐍 dashboard.py
        ├── 🔧 setup.sh
        ├── 📄 requirements.txt
        ├── 📄 .env
        ├── 📄 .env.example
        └── 📊 sensor_data_room1.csv
    

## 1. Getting Started 🛠️
#### &emsp; 1.1 Prerequisites<br/>
   &emsp; Ensure you have the following installed:<br/>
   * OpenSSL: Required for generating security certificates.<br/>
   * Mosquitto Tools: `mosquitto` + `mosquitto_passwd` for broker and credential management.<br/>
   * Python 3.x: For the subscriber and data processing<br/>
   * Arduino IDE: For flashing the ESP32<br/>
   
#### &emsp; 1.2 Environment Setup<br/>
&emsp; Create a virtual environment
```bash
python -m venv venv
```
&emsp; Activate the environment
```bash
# For Windows:
venv\Scripts\activate

# For Linux/macOS:
source venv/bin/activate
```
&emsp; Install dependencies
```bash
pip install -r requirements.txt
``` 

## 2. Credentials Setup (Local Only) 🔒
<blockquote style="background-color: #ffeef0; padding: 10px;">
    <strong>⚠️ Warning:</strong> Sensitive files and local configurations are excluded from Git for security. This includes:
    <ul>
        <li><code>pki/</code> and <code>certs/</code> folders</li>
        <li><code>mosquitto.conf</code>, <code>passwd</code>, and <code>acl</code></li>
        <li><code>.env</code> and <code>sensor_data_room1.csv</code></li>
    </ul>
    You must create or configure them locally by running <code>setup.sh</code>.
</blockquote>

### ⚡ Automated Setup

Run the provided setup script — it handles **everything** in one go:

```bash
chmod +x setup.sh
./setup.sh
```

The script will interactively ask for:

| Prompt | Description |
| :--- | :--- |
| Broker IP Address | Your machine's local IP (e.g. `192.168.1.100`) — used as CN in certificates |
| Certificate validity | Days until cert expiry (default: 365) |
| MQTT Username | Username for ESP32 & subscriber authentication |
| MQTT Password | Secure password (input hidden, with confirmation) |
| Data Topic | e.g. `sensor/suhu/room1` |
| Status/LWT Topic | e.g. `sensor/suhu/room1/status` |

It then automatically generates:
- `pki/ca.key` + `certs/ca.crt` — Certificate Authority
- `certs/server.key` + `certs/server.crt` — Signed server certificate
- `config/passwd` — Hashed Mosquitto password file
- `security/acl` — Access control rules
- `config/mosquitto.conf` — Ready-to-use broker config (absolute paths)
- `.env` — Python subscriber credentials

<blockquote style="background-color: #ffeef0; padding: 10px;">
    <strong>⚠️ Note:</strong> If <code>pki/ca.key</code> and <code>certs/ca.crt</code> already exist, the script skips PKI generation automatically to avoid overwriting existing certificates.
</blockquote>

---

## 3. Execution 🚀
#### &emsp;**3.1 ESP32 Setup**
* Navigate to the `edge/` folder.
* Rename `secrets.h.example` to `secrets.h`.
* Update your WiFi/MQTT credentials and paste the content of `certs/ca.crt` into the `SECRET_CA_CERT` variable.
* Flash `esp32_publisher.ino` to your device. Ensure the Serial Monitor (115200) shows "Time synced!" to allow SSL validation.

#### &emsp;**3.2 Running the System**
&emsp; Open separate terminals:
* Terminal 1 (Broker):
  ![WhatsApp Image 2026-02-19 at 12 40 06](https://github.com/user-attachments/assets/0f8b3459-b93a-4af6-9752-c05a0344690c)

* Terminal 2 (Publisher) Arduino-IDE:
   ![WhatsApp Image 2026-02-19 at 12 41 26](https://github.com/user-attachments/assets/01a7ed16-5910-490c-a999-ba2876780b20)

* Terminal 3 (Subscriber):
  ```bash
  python3 app_subscriber.py
  ```

* Terminal 4 (Dashboard — optional):
  ```bash
  python3 dashboard.py
  ```

## 📊 Data Output Example
### 🖥️ Console Output
When the data buffer reaches the threshold (default: 5), the subscriber calculates and displays averages:
```text
✅ Data Validated & Received: {'temperature': 29.6, 'humidity': 90.7, 'timestamp': '2026-02-21 09:53:34'} | Total: 5
Average Temperature     : 29.6°C
Average Humidity        : 90.74%
--- [ LIVE PANDAS DATAFRAME UPDATED ] ---
```

### 📄 CSV structure
The processed data is automatically saved to `sensor_data_room1.csv`.
| Temperature | Humidity | Timestamp |
| :--- | :--- | :--- |
| 29.9 | 90.8 | 2026-02-16 22:12:06 |
| 29.9 | 90.8 | 2026-02-16 22:12:16 |
| 29.9 | 90.7 | 2026-02-16 22:12:26|

## 🧠 Error Handling SOP
| Error Code / Message | Probable Cause | Recommended Solution |
| :--- | :--- | :--- |
| rc = -1 | Network or Socket Error.| Check WiFi connectivity on ESP32 or verify if the Broker IP is reachable. |
| cert verify failed | Certificate or Time Mismatch. | Ensure ca.crt on ESP32 matches the Broker. Verify that NTP time sync on ESP32 was successful. |
| Auth Failed (RC 4/5) | Credential Mismatch. | Check if the username and password in secrets.h match the config/passwd file.|
| NaN on Sensor| Physical hardware failure. | Check the wiring of the DHT22 sensor. Ensure the sensor has adequate power supply.|

## 📜 License
This project is licensed under the Apache License — feel free to use, modify, and distribute.

## 🧑‍💻 Author
Suprapto Santoso<br/>
AI & IoT Developer<br/>
🚀 Focused on Generative AI, Embedded Systems, and Smart Automation<br/>
supraptosantoso.san@gmail.com