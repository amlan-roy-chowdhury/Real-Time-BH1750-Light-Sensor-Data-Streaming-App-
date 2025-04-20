# src/config.py
import os
from dotenv import load_dotenv

load_dotenv()

# MQTT
MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_TOPIC = "sensor/lux"

# Adafruit IO
AIO_USERNAME = 'arc2233'
AIO_KEY = os.getenv("ADAFRUIT_IO_KEY")
AIO_FEED = 'light-sensor'

# AWS S3
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_S3_BUCKET = os.getenv("AWS_S3_BUCKET")

# Paths
DEFAULT_LOG_DIR = os.path.join(os.path.dirname(__file__), '..', 'logs')
UPDATE_INTERVAL_MS = 100
AIO_SEND_INTERVAL_SEC = 2
