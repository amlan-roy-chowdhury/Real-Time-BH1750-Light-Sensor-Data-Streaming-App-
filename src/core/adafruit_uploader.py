# src/core/adafruit_uploader.py
from Adafruit_IO import Client
from config import AIO_USERNAME, AIO_KEY, AIO_FEED

aio = Client(AIO_USERNAME, AIO_KEY)

def send_to_adafruit(lux):
    try:
        aio.send(AIO_FEED, lux)
        print(f"[Adafruit IO] Uploaded Lux: {lux}")
        return True
    except Exception as e:
        print(f"[Adafruit IO] Error: {e}")
        return False
