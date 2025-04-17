import json
import random
import time
from PyQt5.QtTest import QTest

def simulate_mqtt_message(app, lux_value):
    """Simulate receiving a valid MQTT message with a given lux value"""
    payload = json.dumps({"lux": lux_value})
    msg = type('MQTTMessage', (object,), {'payload': payload.encode()})()
    app.append_data(lux_value)
    return msg

def simulate_serial_line(app, lux_value):
    """Simulate receiving a serial line with a timestamp,lux format"""
    timestamp = int(time.time() * 1000)
    line = f"{timestamp},{lux_value}"
    app.process_data_line(line)

def simulate_invalid_serial(app):
    """Send malformed serial line"""
    app.process_data_line("invalid,data")

def simulate_invalid_json(app):
    """Send malformed MQTT JSON"""
    msg = type('MQTTMessage', (object,), {'payload': b"{bad:json}"})()
    try:
        app.append_data(msg)
    except Exception as e:
        print("[TEST] Handled bad JSON:", e)
