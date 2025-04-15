import sys
import time
import csv
import json
import serial
import serial.tools.list_ports
import paho.mqtt.client as mqtt
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QPushButton,
                             QLabel, QComboBox, QHBoxLayout, QFileDialog)
from PyQt5.QtCore import QTimer
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from threading import Thread, Event
from collections import deque

# --- CONFIGURATION ---
MQTT_BROKER = "localhost"
MQTT_TOPIC = "sensor/lux"
CLOUD_SYNC = False
CSV_FILE = "lux_log.csv"

# --- GUI CLASS ---
class SensorDashboard(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.plot_data = deque(maxlen=500)
        self.timestamps = deque(maxlen=500)
        self.running = False
        self.serial_port = None
        self.serial_thread = None
        self.mqtt_thread = None
        self.mqtt_client = None
        self.stop_event = Event()
        self.timer_offset = 0
        self.timer_start_time = None

    def init_ui(self):
        self.setWindowTitle("Real-Time Sensor Dashboard")

        self.com_label = QLabel("Select COM Port:")
        self.com_dropdown = QComboBox()
        self.refresh_com_ports()

        self.start_btn = QPushButton("Start")
        self.stop_btn = QPushButton("Stop")
        self.clear_btn = QPushButton("Clear")
        self.reset_btn = QPushButton("Reset Timer")

        self.stop_btn.setEnabled(False)

        hbox = QHBoxLayout()
        hbox.addWidget(self.com_label)
        hbox.addWidget(self.com_dropdown)
        hbox.addWidget(self.start_btn)
        hbox.addWidget(self.stop_btn)
        hbox.addWidget(self.clear_btn)
        hbox.addWidget(self.reset_btn)

        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)
        self.ax.set_xlabel("Time (ms)")
        self.ax.set_ylabel("Lux")

        layout = QVBoxLayout()
        layout.addLayout(hbox)
        layout.addWidget(self.canvas)
        self.setLayout(layout)

        self.start_btn.clicked.connect(self.start_stream)
        self.stop_btn.clicked.connect(self.stop_stream)
        self.clear_btn.clicked.connect(self.clear_plot)
        self.reset_btn.clicked.connect(self.reset_timer)

    def refresh_com_ports(self):
        self.com_dropdown.clear()
        ports = serial.tools.list_ports.comports()
        for port in ports:
            self.com_dropdown.addItem(port.device)

    def start_stream(self):
        self.running = True
        self.stop_event.clear()
        self.timer_start_time = time.time()
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        selected_port = self.com_dropdown.currentText()
        if selected_port:
            self.serial_thread = Thread(target=self.read_serial, args=(selected_port,), daemon=True)
            self.serial_thread.start()
        else:
            self.mqtt_thread = Thread(target=self.read_mqtt, daemon=True)
            self.mqtt_thread.start()
        self.update_plot()

    def stop_stream(self):
        self.running = False
        self.stop_event.set()
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def clear_plot(self):
        self.plot_data.clear()
        self.timestamps.clear()
        self.ax.cla()
        self.ax.set_xlabel("Time (ms)")
        self.ax.set_ylabel("Lux")
        self.canvas.draw()

    def reset_timer(self):
        self.timer_offset = 0
        self.timer_start_time = time.time()
        self.clear_plot()

    def read_serial(self, port):
        try:
            with serial.Serial(port, 115200, timeout=1) as ser:
                while self.running and not self.stop_event.is_set():
                    line = ser.readline().decode().strip()
                    if line:
                        self.process_data_line(line)
        except Exception as e:
            print(f"Serial error: {e}")

    def read_mqtt(self):
        def on_connect(client, userdata, flags, rc):
            client.subscribe(MQTT_TOPIC)

        def on_message(client, userdata, msg):
            payload = json.loads(msg.payload.decode())
            timestamp = payload.get("timestamp")
            lux = payload.get("lux")
            self.timestamps.append(timestamp)
            self.plot_data.append(lux)
            self.log_to_csv(timestamp, lux)

        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_connect = on_connect
        self.mqtt_client.on_message = on_message
        self.mqtt_client.connect(MQTT_BROKER, 1883, 60)
        self.mqtt_client.loop_start()
        while self.running and not self.stop_event.is_set():
            time.sleep(0.1)
        self.mqtt_client.loop_stop()
        self.mqtt_client.disconnect()

    def process_data_line(self, line):
        try:
            parts = line.split(",")
            if len(parts) == 2:
                timestamp = int(float(parts[0]))
                lux = float(parts[1])
                elapsed_time = int((time.time() - self.timer_start_time) * 1000)
                self.timestamps.append(elapsed_time)
                self.plot_data.append(lux)
                self.log_to_csv(elapsed_time, lux)
        except ValueError:
            pass

    def update_plot(self):
        if self.running:
            self.ax.cla()
            self.ax.plot(list(self.timestamps), list(self.plot_data), label="Lux", color="blue")
            self.ax.set_xlabel("Time (ms)")
            self.ax.set_ylabel("Lux")
            self.ax.set_title("Real-Time Light Sensor Data")
            self.ax.legend()
            self.ax.grid(True)
            self.canvas.draw()
            QTimer.singleShot(100, self.update_plot)

    def log_to_csv(self, timestamp, lux):
        with open(CSV_FILE, mode='a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([timestamp, lux])

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = SensorDashboard()
    window.show()
    sys.exit(app.exec_())