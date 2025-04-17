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
  Serial.begin(115200);
  Wire.begin();
  lightMeter.begin();

  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.println("Connecting to WiFi...");
  }
  Serial.println("Connected to WiFi");

  // Setup MQTT
  client.setServer(mqtt_server, 1883);
  client.setKeepAlive(60); // <-- this is how you set keepalive time

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

void reconnect() {
  while (!client.connected()) {
    Serial.print("Reconnecting to MQTT...");
    if (client.connect("ESP32Client")) {
      Serial.println("connected");
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" trying again in 5 seconds");
      delay(5000);
    }
  }
}

void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();

  unsigned long now = millis();
  if (now - lastSend >= interval) {
    lastSend = now;

    float lux = lightMeter.readLightLevel();
    Serial.printf("%lu,%.2f\n", now, lux);

    char payload[64];
    snprintf(payload, sizeof(payload), "{\"timestamp\":%lu,\"lux\":%.2f}", now, lux);
    client.publish("sensor/lux", payload);
  }
}