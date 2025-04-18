import sys
import time
import csv
import json
import serial
import os
import serial.tools.list_ports
import paho.mqtt.client as mqtt
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QPushButton,
                             QLabel, QComboBox, QHBoxLayout, QGroupBox,
                             QRadioButton, QButtonGroup, QFileDialog)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from threading import Thread, Event
from collections import deque
import datetime
from Adafruit_IO import Client
from dotenv import load_dotenv

load_dotenv()

MQTT_BROKER = "localhost"
MQTT_TOPIC = "sensor/lux"
CSV_FILE = "lux_log.csv"
AIO_USERNAME = 'arc2233'
AIO_KEY = os.getenv("ADAFRUIT_IO_KEY")
AIO_FEED = 'light-sensor'

aio = Client(AIO_USERNAME, AIO_KEY)

class SensorDashboard(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.relative_data = deque(maxlen=500)
        self.relative_timestamps = deque(maxlen=500)
        self.gmt_data = deque(maxlen=500)
        self.gmt_timestamps = deque(maxlen=500)
        self.running = False
        self.serial_thread = None
        self.mqtt_thread = None
        self.mqtt_client = None
        self.stop_event = Event()
        self.timer_start_time = None
        self.timestamp_mode = "Relative"
        self.last_aio_send_time = 0
        self.paused = False

    def init_ui(self):
        self.setWindowTitle("Real-Time Sensor Dashboard")

        # Stream Mode Group
        stream_group = QGroupBox("Data Stream Mode")
        self.wifi_radio = QRadioButton("WiFi")
        self.com_radio = QRadioButton("COM")
        self.wifi_radio.setChecked(True)
        self.mode_group = QButtonGroup()
        self.mode_group.addButton(self.wifi_radio)
        self.mode_group.addButton(self.com_radio)
        self.mode_group.buttonClicked.connect(self.toggle_stream_mode)
        stream_layout = QVBoxLayout()
        stream_layout.addWidget(self.wifi_radio)
        stream_layout.addWidget(self.com_radio)
        stream_group.setLayout(stream_layout)

        # COM Dropdown
        self.com_label = QLabel("Select COM Port:")
        self.com_dropdown = QComboBox()
        self.refresh_com_ports()
        self.com_dropdown.setEnabled(False)

        # Time Axis Group
        time_group = QGroupBox("Time Axis Mode")
        self.relative_radio = QRadioButton("Relative")
        self.gmt_radio = QRadioButton("GMT")
        self.relative_radio.setChecked(True)
        self.time_group = QButtonGroup()
        self.time_group.addButton(self.relative_radio)
        self.time_group.addButton(self.gmt_radio)
        self.time_group.buttonClicked.connect(self.toggle_time_mode)
        time_layout = QVBoxLayout()
        time_layout.addWidget(self.relative_radio)
        time_layout.addWidget(self.gmt_radio)
        time_group.setLayout(time_layout)

        # Button Group
        control_box = QGroupBox("Controls")
        self.start_btn = QPushButton("Start")
        self.pause_btn = QPushButton("Pause")
        self.stop_btn = QPushButton("Stop")
        self.clear_btn = QPushButton("Clear")
        self.reset_btn = QPushButton("Reset Timer")
        self.export_btn = QPushButton("Export CSV")
        self.stop_btn.setEnabled(False)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.start_btn)
        button_layout.addWidget(self.pause_btn)
        button_layout.addWidget(self.stop_btn)
        button_layout.addWidget(self.clear_btn)
        button_layout.addWidget(self.reset_btn)
        control_box.setLayout(button_layout)

        self.current_lux_label = QLabel("Current Lux: --")
        self.current_lux_label.setAlignment(Qt.AlignCenter)
        self.current_lux_label.setStyleSheet("font-size: 20px; font-weight: bold;")

        self.adafruit_status = QLabel("Adafruit IO: Waiting...")
        self.adafruit_status.setAlignment(Qt.AlignCenter)
        self.adafruit_status.setStyleSheet("color: gray; font-size: 14px;")

        self.min_label = QLabel("Min: --")
        self.max_label = QLabel("Max: --")
        self.avg_label = QLabel("Avg: --")
        
        for lbl in [self.min_label, self.max_label, self.avg_label]:
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("""
                border: 1px solid gray;
                padding: 4px;
                font-size: 14px;
                border-radius: 4px;
                min-width: 80px;
            """)
            
        # Last Updated Timestamp Label
        self.updated_label = QLabel("Last Updated: --")
        self.updated_label.setAlignment(Qt.AlignCenter)
        self.updated_label.setStyleSheet("""
            font-size: 11px;
            font-style: italic;
            color: gray;
            margin-top: 4px;
        """)
        
        # Warning alert
        self.warning_label = QLabel("Please clear the plot before restarting.")
        self.warning_label.setAlignment(Qt.AlignCenter)
        self.warning_label.setStyleSheet("""
            font-size: 11px;
            font-style: italic;
            color: darkred;
        """)
        self.warning_label.hide()



        controls = QHBoxLayout()
        controls.addWidget(stream_group)
        controls.addWidget(self.com_label)
        controls.addWidget(self.com_dropdown)
        controls.addWidget(time_group)
        controls.addWidget(self.export_btn)

        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)
        self.ax.set_xlabel("Time")
        self.ax.set_ylabel("Lux")

        # Create stats layout with borders and spacing
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(15)
        stats_layout.addStretch()
        stats_layout.addWidget(self.min_label)
        stats_layout.addWidget(self.max_label)
        stats_layout.addWidget(self.avg_label)
        stats_layout.addStretch()

        # Main layout setup
        layout = QVBoxLayout()
        layout.addLayout(controls)
        layout.addWidget(control_box)
        layout.addWidget(self.canvas)
        layout.addWidget(self.warning_label)
        layout.addWidget(self.current_lux_label)
        layout.addWidget(self.adafruit_status)
        layout.addLayout(stats_layout) 
        layout.addLayout(stats_layout)
        layout.addWidget(self.updated_label)
        self.setLayout(layout)

        self.start_btn.clicked.connect(self.start_stream)
        self.stop_btn.clicked.connect(self.stop_stream)
        self.clear_btn.clicked.connect(self.clear_plot)
        self.reset_btn.clicked.connect(self.reset_timer)
        self.export_btn.clicked.connect(self.export_csv)
        self.pause_btn.clicked.connect(self.toggle_pause)

    def toggle_stream_mode(self):
        self.com_dropdown.setEnabled(self.com_radio.isChecked())

    def toggle_time_mode(self):
        self.timestamp_mode = "Relative" if self.relative_radio.isChecked() else "GMT"

    def toggle_pause(self):
        self.paused = not self.paused
        self.pause_btn.setText("Resume" if self.paused else "Pause")

    def refresh_com_ports(self):
        self.com_dropdown.clear()
        ports = serial.tools.list_ports.comports()
        detected_sensor_port = None

        for port in ports:
            try:
                with serial.Serial(port.device, 115200, timeout=1) as ser:
                    line = ser.readline().decode().strip()
                    parts = line.split(",")
                    if len(parts) == 2:
                        float(parts[1])  # If second value is a float, it’s a sensor
                        detected_sensor_port = port.device
                        break
            except:
                continue

        for port in ports:
            label = f"{port.device} (Detected Sensor Port)" if port.device == detected_sensor_port else port.device
            self.com_dropdown.addItem(label)

        if detected_sensor_port:
            self.com_dropdown.setCurrentIndex(
                self.com_dropdown.findText(f"{detected_sensor_port} (Detected Sensor Port)")
            )
        
        
    def start_stream(self):
        if self.running:
            return
        self.running = True
        self.stop_event.clear()
        self.timer_start_time = time.time()
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

        if self.com_radio.isChecked():
            selected_label = self.com_dropdown.currentText()
            selected_port = selected_label.split(" ")[0]  # Extract port before any label
            if selected_port:
                self.serial_thread = Thread(target=self.read_serial, args=(selected_port,), daemon=True)
                self.serial_thread.start()
        else:
            self.mqtt_thread = Thread(target=self.read_mqtt, daemon=True)
            self.mqtt_thread.start()

        QTimer.singleShot(100, self.update_plot)

    def stop_stream(self):
        self.running = False
        self.stop_event.set()
        self.start_btn.setEnabled(False)
        self.warning_label.show()
        self.stop_btn.setEnabled(False)
        if self.mqtt_client:
            try:
                self.mqtt_client.loop_stop()
                self.mqtt_client.disconnect()
            except Exception as e:
                print(f"[MQTT] Cleanup Error: {e}")
            finally:
                self.mqtt_client = None


    def clear_plot(self):
        self.relative_data.clear()
        self.relative_timestamps.clear()
        self.gmt_data.clear()
        self.gmt_timestamps.clear()
        self.ax.cla()
        self.ax.set_xlabel("Time (ms)")
        self.ax.set_ylabel("Lux")
        self.canvas.draw()
        self.start_btn.setEnabled(True)
        self.warning_label.hide()


    def reset_timer(self):
        self.timer_start_time = time.time()
        self.clear_plot()

    def export_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export CSV", "lux_data.csv", "CSV files (*.csv)")
        if path:
            with open(path, mode='w', newline='') as outfile:
                writer = csv.writer(outfile)
                writer.writerow(["Timestamp", "Lux"])
                for ts, lux in zip(self.gmt_timestamps, self.gmt_data):
                    writer.writerow([ts, lux])

    def send_to_adafruit(self, lux):
        try:
            aio.send(AIO_FEED, lux)
            self.adafruit_status.setText("Adafruit IO: Updated")
            self.adafruit_status.setStyleSheet("color: green; font-size: 14px;")
        except Exception as e:
            print(f"[Adafruit IO] Error: {e}")
            self.adafruit_status.setText("Adafruit IO: Error")
            self.adafruit_status.setStyleSheet("color: red; font-size: 14px;")

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
            return

        last_aio_send_time = 0

        def on_connect(client, userdata, flags, rc):
            client.subscribe(MQTT_TOPIC)

        def on_message(client, userdata, msg):
            nonlocal last_aio_send_time
            try:
                payload = json.loads(msg.payload.decode())
                lux = payload.get("lux")
                if lux is not None:
                    self.append_data(lux)
                    current_time = time.time()
                    if current_time - last_aio_send_time >= 2:
                        last_aio_send_time = current_time
                        Thread(target=self.send_to_adafruit, args=(lux,), daemon=True).start()
            except Exception as e:
                print(f"[MQTT] Error: {e}")

        try:
            self.mqtt_client = mqtt.Client(client_id="DashboardClient")
            self.mqtt_client.on_connect = on_connect
            self.mqtt_client.on_message = on_message
            self.mqtt_client.connect(MQTT_BROKER, 1883, 60)
            self.mqtt_client.loop_start()

            while self.running and not self.stop_event.is_set():
                time.sleep(0.1)

            if self.mqtt_client:
                try:
                    self.mqtt_client.loop_stop()
                    self.mqtt_client.disconnect()
                except Exception as e:
                    print(f"[MQTT] Cleanup Error: {e}")
                finally:
                    self.mqtt_client = None

        except Exception as e:
            print(f"[MQTT] Connection Error: {e}")

    def process_data_line(self, line):
        try:
            parts = line.split(",")
            if len(parts) == 2:
                lux = float(parts[1])
                self.append_data(lux)
                current_time = time.time()
                if current_time - self.last_aio_send_time >= 2:
                    self.last_aio_send_time = current_time
                    Thread(target=self.send_to_adafruit, args=(lux,), daemon=True).start()
        except ValueError:
            pass

    def append_data(self, lux):
        if self.paused:
            return
        now = time.time()
        if self.timer_start_time is None:
            self.timer_start_time = now
        rel_ts = int((now - self.timer_start_time) * 1000)
        gmt_ts = datetime.datetime.utcnow()
        self.relative_timestamps.append(rel_ts)
        self.relative_data.append(lux)
        self.gmt_timestamps.append(gmt_ts)
        self.gmt_data.append(lux)
        self.log_to_csv(gmt_ts, lux)

        self.current_lux_label.setText(f"Current Lux: {lux:.2f}")
        self.min_label.setText(f"Min: {min(self.gmt_data):.2f}")
        self.max_label.setText(f"Max: {max(self.gmt_data):.2f}")
        self.avg_label.setText(f"Avg: {sum(self.gmt_data)/len(self.gmt_data):.2f}")
        self.updated_label.setText(f"Last Updated: {gmt_ts.strftime('%H:%M:%S')}")


    def update_plot(self):
        if self.running:
            self.ax.cla()
            if self.timestamp_mode == "GMT":
                timestamps_copy = list(self.gmt_timestamps)
                data = list(self.gmt_data)
                times = [ts.strftime("%H:%M:%S") for ts in timestamps_copy]
                self.ax.set_xlabel("Time (GMT)")
            else:
                times = list(self.relative_timestamps)
                data = list(self.relative_data)
                self.ax.set_xlabel("Time (ms)")

            self.ax.plot(times, data, label="Lux", color="blue")
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
            
    def closeEvent(self, event):
        self.stop_stream()  # Gracefully stop everything
        super().closeEvent(event)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = SensorDashboard()
    window.show()
    sys.exit(app.exec_())