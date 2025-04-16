#include <Wire.h>
#include <BH1750.h>
#include <WiFi.h>
#include <PubSubClient.h>

//Wifi Credentials

const char* ssid = "Code&Chill";
const char* password = "4ttack+itVn";

const char* mqtt_server = "192.168.1.188"; // MQTT Broker IP

WiFiClient espClient;
PubSubClient client(espClient);
BH1750 lightMeter;

unsigned long lastSend = 0;
const int interval = 10;  // 100 Hz = every 10 ms

void setup() {
  Serial.begin(115200);     // UART Output
  Wire.begin();             // I2C init
  lightMeter.begin();       // BH1750 in CONTINUOUS_HIGH_RES_MODE

  // --- Connect to WiFi ---
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.println("Connecting to WiFi...");
  }
  Serial.println("Connected to WiFi");

  // --- MQTT Setup ---
  client.setServer(mqtt_server, 1883);
  while (!client.connected()) {
    Serial.print("Connecting to MQTT...");
    if (client.connect("ESP32Client")) {
      Serial.println("Connected!");
    } else {
      Serial.print("Failed, rc=");
      Serial.print(client.state());
      Serial.println(" try again in 5 seconds");
      delay(5000);
    }
  }
}

void loop() {
  // MUST be called every loop to keep MQTT alive
  client.loop();

  unsigned long now = millis();
  if (now - lastSend >= interval) {
    lastSend = now;

    float lux = lightMeter.readLightLevel();

    // UART output (required)
    Serial.printf("%lu,%.2f\n", now, lux);

    // MQTT output (wireless)
    if (client.connected()) {
      char payload[64];
      snprintf(payload, sizeof(payload), "{\"timestamp\":%lu,\"lux\":%.2f}", now, lux);
      client.publish("sensor/lux", payload);
    }
  }
}