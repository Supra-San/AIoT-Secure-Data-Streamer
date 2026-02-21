#include <DHT.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include "secrets.h" // Import separate credentials

// --- Constants ---
#define DHTPIN 4
#define DHTTYPE DHT22
const char* NTP_SERVER_1 = "0.pool.ntp.org";
const char* NTP_SERVER_2 = "time.google.com";
const long  GMT_OFFSET_SEC = 7 * 3600; // GMT+7
const int   DAYLIGHT_OFFSET_SEC = 0;

// --- Global Objects ---
DHT dht(DHTPIN, DHTTYPE);
WiFiClientSecure espClient;
PubSubClient client(espClient);

// --- Function Prototypes ---
void setupWiFi();
void setupTime();
void reconnect();

void setupWiFi() {
    Serial.println("\nConnecting to WiFi...");
    WiFi.begin(SECRET_SSID, SECRET_PASS);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.println("\nWiFi Connected. IP: " + WiFi.localIP().toString());
}

// Time synchronization (Required for SSL Certificate validation)
void setupTime() {
    configTime(GMT_OFFSET_SEC, DAYLIGHT_OFFSET_SEC, NTP_SERVER_1, NTP_SERVER_2);
    Serial.print("Waiting for NTP time sync: ");
    time_t now = time(nullptr);
    while (now < 8 * 3600 * 2) {
        delay(500);
        Serial.print(".");
        now = time(nullptr);
    }
    Serial.println("Time synced!");
}

void reconnect() {
    while (!client.connected()) {
        Serial.print("Attempting MQTT connection (TLS/SSL)...");
        
        // Last Will and Testament (LWT) implementation
        // Automatically sends "offline" message if connection is lost unexpectedly
        if (client.connect("ESP32_Client", SECRET_MQTT_USER, SECRET_MQTT_PASS, 
                           STATUS_TOPIC, 1, true, "offline")) {
            Serial.println("connected!");
            client.publish(STATUS_TOPIC, "online", true); // Send online status
        } else {
            Serial.print("failed, rc=");
            Serial.print(client.state());
            Serial.println(" retrying in 5 seconds...");
            delay(5000);
        }
    }
}

// Setup function
void setup() {
    Serial.begin(115200);
    dht.begin();
    setupWiFi();
    setupTime(); 

    // Security Configuration
    espClient.setCACert(SECRET_CA_CERT); // Set CA Certificate
    client.setBufferSize(512);
    client.setServer(SECRET_MQTT_BROKER, SECRET_MQTT_PORT);
}

void loop() {
    if (!client.connected()) {
        reconnect();
    }
    client.loop();

    static unsigned long lastMsg = 0;
    unsigned long now = millis();
    if (now - lastMsg > 10000) { // Publish data every 10 seconds
        lastMsg = now;

        float h = dht.readHumidity();
        float t = dht.readTemperature();

        if (isnan(h) || isnan(t)) {
            Serial.println("Failed to read from DHT sensor!");
            return;
        }

        // JSON Payload Format (Industry Standard)
        String payload = "{\"temperature\":" + String(t) + ",\"humidity\":" + String(h) + "}";
        
        Serial.print("Publishing to " + String(DATA_TOPIC) + ": ");
        Serial.println(payload);
        
        // Publish via encrypted path Port 8883
        client.publish(DATA_TOPIC, payload.c_str());
    }
}