import sys
import time
import csv
import json
import serial
import serial.tools.list_ports
import paho.mqtt.client as mqtt
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QPushButton,
                             QLabel, QComboBox, QHBoxLayout, QFileDialog,
                             QRadioButton, QButtonGroup)
from PyQt5.QtCore import QTimer, Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from threading import Thread, Event
from collections import deque
import datetime

MQTT_BROKER = "localhost"
MQTT_TOPIC = "sensor/lux"
CSV_FILE = "lux_log.csv"

class SensorDashboard(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.plot_data = deque(maxlen=500)
        self.timestamps = deque(maxlen=500)
        self.running = False
        self.serial_thread = None
        self.mqtt_thread = None
        self.mqtt_client = None
        self.stop_event = Event()
        self.timer_start_time = None
        self.timestamp_mode = "Relative"

    def init_ui(self):
        self.setWindowTitle("Real-Time Sensor Dashboard")

        # Stream mode
        self.stream_mode_label = QLabel("Data Stream Mode:")
        self.wifi_radio = QRadioButton("WiFi")
        self.com_radio = QRadioButton("COM")
        self.wifi_radio.setChecked(True)
        self.mode_group = QButtonGroup()
        self.mode_group.addButton(self.wifi_radio)
        self.mode_group.addButton(self.com_radio)
        self.mode_group.buttonClicked.connect(self.toggle_stream_mode)

        # COM dropdown
        self.com_label = QLabel("Select COM Port:")
        self.com_dropdown = QComboBox()
        self.com_dropdown.setEnabled(False)
        self.refresh_com_ports()

        # Time mode
        self.time_mode_label = QLabel("Time Axis Mode:")
        self.relative_radio = QRadioButton("Start from 0")
        self.gmt_radio = QRadioButton("GMT")
        self.relative_radio.setChecked(True)
        self.time_group = QButtonGroup()
        self.time_group.addButton(self.relative_radio)
        self.time_group.addButton(self.gmt_radio)
        self.time_group.buttonClicked.connect(self.toggle_time_mode)

        # Buttons
        self.start_btn = QPushButton("Start")
        self.stop_btn = QPushButton("Stop")
        self.clear_btn = QPushButton("Clear")
        self.reset_btn = QPushButton("Reset Timer")
        self.stop_btn.setEnabled(False)

        # Layouts
        stream_box = QHBoxLayout()
        stream_box.addWidget(self.stream_mode_label)
        stream_box.addWidget(self.wifi_radio)
        stream_box.addWidget(self.com_radio)

        time_box = QHBoxLayout()
        time_box.addWidget(self.time_mode_label)
        time_box.addWidget(self.relative_radio)
        time_box.addWidget(self.gmt_radio)

        hbox = QHBoxLayout()
        hbox.addLayout(stream_box)
        hbox.addWidget(self.com_label)
        hbox.addWidget(self.com_dropdown)
        hbox.addLayout(time_box)
        hbox.addWidget(self.start_btn)
        hbox.addWidget(self.stop_btn)
        hbox.addWidget(self.clear_btn)
        hbox.addWidget(self.reset_btn)

        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)
        self.ax.set_xlabel("Time")
        self.ax.set_ylabel("Lux")

        layout = QVBoxLayout()
        layout.addLayout(hbox)
        layout.addWidget(self.canvas)
        self.setLayout(layout)

        # Events
        self.start_btn.clicked.connect(self.start_stream)
        self.stop_btn.clicked.connect(self.stop_stream)
        self.clear_btn.clicked.connect(self.clear_plot)
        self.reset_btn.clicked.connect(self.reset_timer)

    def toggle_stream_mode(self):
        self.com_dropdown.setEnabled(self.com_radio.isChecked())

    def toggle_time_mode(self):
        self.timestamp_mode = "Relative" if self.relative_radio.isChecked() else "GMT"

    def refresh_com_ports(self):
        self.com_dropdown.clear()
        ports = serial.tools.list_ports.comports()
        for port in ports:
            self.com_dropdown.addItem(port.device)

    def start_stream(self):
        if self.running:
            return
        self.running = True
        self.stop_event.clear()
        self.timer_start_time = time.time()
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

        if self.com_radio.isChecked():
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

        if self.mqtt_client:
            try:
                self.mqtt_client.loop_stop()
                self.mqtt_client.disconnect()
            except:
                pass
            self.mqtt_client = None

    def clear_plot(self):
        self.plot_data.clear()
        self.timestamps.clear()
        self.ax.cla()
        self.ax.set_xlabel("Time")
        self.ax.set_ylabel("Lux")
        self.canvas.draw()

    def reset_timer(self):
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
        if self.mqtt_client is not None and self.mqtt_thread and self.mqtt_thread.is_alive():
            print("MQTT already running.")
            return

        def on_connect(client, userdata, flags, rc):
            client.subscribe(MQTT_TOPIC)

        def on_message(client, userdata, msg):
            payload = json.loads(msg.payload.decode())
            lux = payload.get("lux")
            if self.timer_start_time is None:
                self.timer_start_time = time.time()
            if self.timestamp_mode == "GMT":
                timestamp = datetime.datetime.utcnow()
                self.timestamps.append(timestamp)
            else:
                elapsed_time = int((time.time() - self.timer_start_time) * 1000)
                self.timestamps.append(elapsed_time)
            self.plot_data.append(lux)
            self.log_to_csv(self.timestamps[-1], lux)

        try:
            self.mqtt_client = mqtt.Client(client_id="DashboardClient")
            self.mqtt_client.on_connect = on_connect
            self.mqtt_client.on_message = on_message
            self.mqtt_client.connect(MQTT_BROKER, 1883, 60)
            self.mqtt_client.loop_start()

            while self.running and not self.stop_event.is_set():
                time.sleep(0.1)

            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
            self.mqtt_client = None

        except Exception as e:
            print(f"MQTT error: {e}")

    def process_data_line(self, line):
        try:
            parts = line.split(",")
            if len(parts) == 2:
                lux = float(parts[1])
                if self.timestamp_mode == "GMT":
                    timestamp = datetime.datetime.utcnow()
                    self.timestamps.append(timestamp)
                else:
                    elapsed_time = int((time.time() - self.timer_start_time) * 1000)
                    self.timestamps.append(elapsed_time)
                self.plot_data.append(lux)
                self.log_to_csv(self.timestamps[-1], lux)
        except ValueError:
            pass

    def update_plot(self):
        if self.running:
            self.ax.cla()
            if self.timestamp_mode == "GMT":
                times = [ts.strftime("%H:%M:%S") for ts in self.timestamps]
                self.ax.set_xlabel("Time (GMT)")
            else:
                times = self.timestamps
                self.ax.set_xlabel("Time (ms)")

            self.ax.plot(times, list(self.plot_data), label="Lux", color="blue")
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
