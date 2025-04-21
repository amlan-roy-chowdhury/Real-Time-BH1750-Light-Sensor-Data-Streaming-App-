# src/ui/layout.py

import os
import sys
import csv
import time
import json
import serial
import datetime
from threading import Thread, Event
from collections import deque

import serial.tools.list_ports
import paho.mqtt.client as mqtt

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton, QLabel,
    QComboBox, QGroupBox, QRadioButton, QButtonGroup, QFormLayout, QMessageBox
)
from PyQt5.QtCore import Qt, QTimer
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from config import (
    MQTT_BROKER, MQTT_TOPIC, DEFAULT_LOG_DIR,
    AIO_SEND_INTERVAL_SEC
)
from core.adafruit_uploader import send_to_adafruit
from core.s3_uploader import upload_to_s3
from core.data_logger import write_summary_csv, write_temp_log

class SensorDashboard(QWidget):
    def __init__(self):
        super().__init__()
        self.relative_data = deque(maxlen=500)
        self.relative_timestamps = deque(maxlen=500)
        self.gmt_data = deque(maxlen=500)
        self.gmt_timestamps = deque(maxlen=500)
        self.running = False
        self.paused = False
        self.serial_thread = None
        self.mqtt_thread = None
        self.mqtt_client = None
        self.stop_event = Event()
        self.timer_start_time = None
        self.timestamp_mode = "Relative"
        self.last_aio_send_time = 0
        self.session_data = []
        self.logs_dir = DEFAULT_LOG_DIR
        os.makedirs(self.logs_dir, exist_ok=True)
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Real-Time Sensor Dashboard")
        layout = QVBoxLayout()

        # === Stream Mode Group ===
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

        # === COM Port Dropdown ===
        self.com_label = QLabel("Select COM Port:")
        self.com_dropdown = QComboBox()
        self.com_dropdown.setEnabled(False)
        self.refresh_com_ports()
        com_layout = QFormLayout()
        com_layout.addRow(self.com_label, self.com_dropdown)

        # === Time Mode Group ===
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

        # === Export & Recovery Group ===
        export_group = QGroupBox("Data Export / Recovery")
        export_layout = QGridLayout()

        self.export_btn = QPushButton("Export CSV")
        self.recover_btn = QPushButton("Recover from Temp Log")
        self.clear_temp_btn = QPushButton("Clear Temp Log")

        standard_width = 190
        for btn in [self.export_btn, self.recover_btn, self.clear_temp_btn]:
            btn.setFixedWidth(standard_width)
            btn.setStyleSheet("text-align: center; padding: 6px; font-size: 13px;")

        # Tooltips
        self.export_tooltip = QLabel("?")
        self.export_tooltip.setStyleSheet("color: gray; font-size: 14px; font-weight: bold; padding-left: 4px;")
        self.export_tooltip.setToolTipDuration(0)
        self.export_tooltip.setToolTip("""
            <div style="font-size: 12px; color: white; font-style: italic;">
            <b>Export CSV:</b> Saves data from the last Start–Stop session.<br>
            If you don’t export manually, it will be saved as a temp log.<br>
            Saves session to a timestamped file with:
            <ul>
              <li>Lux readings</li>
              <li>Relative & GMT timestamps</li>
              <li>Summary stats like Min, Max, and Avg </li>
            </ul>
            Stored in <code>logs/</code>. If skipped, logs/temp_log.csv will be created.
            </div>
        """)

        self.recover_tooltip = QLabel("?")
        self.recover_tooltip.setStyleSheet("color: gray; font-size: 14px; font-weight: bold; padding-left: 4px;")
        self.recover_tooltip.setToolTipDuration(0)
        self.recover_tooltip.setToolTip("""
            <div style="font-size: 12px; color: white; font-style: italic;">
            Reloads the last unsaved session from temp_log.csv for export or inspection.
            </div>
        """)

        export_layout.addWidget(self.export_btn, 0, 0)
        export_layout.addWidget(self.export_tooltip, 0, 1)
        export_layout.addWidget(self.recover_btn, 1, 0)
        export_layout.addWidget(self.recover_tooltip, 1, 1)
        export_layout.addWidget(self.clear_temp_btn, 2, 0)
        export_group.setLayout(export_layout)

        # === Layout Assembly ===
        top_controls = QHBoxLayout()
        top_controls.addWidget(stream_group)
        top_controls.addLayout(com_layout)
        top_controls.addWidget(time_group)
        top_controls.addStretch()
        top_controls.addWidget(export_group)

        layout.addLayout(top_controls)

        # === Plot Area ===
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        # Add a minimum height to the canvas to prevent clipping
        self.canvas.setMinimumHeight(300)
        self.canvas.setStyleSheet("margin-top: 8px; border: 1px solid #555; border-radius: 4px;")
        self.ax = self.figure.add_subplot(111)
        self.ax.set_xlabel("Time")
        self.ax.set_ylabel("Lux")
        self.figure.subplots_adjust(bottom=0.25)  # Slightly increase from 0.2
        self.setup_control_buttons(layout)
        layout.addWidget(self.canvas)
        

        # Placeholders (to be filled next)
        self.setup_status_labels(layout)

        self.setLayout(layout)

        # Connect core logic
        self.export_btn.clicked.connect(self.export_csv)
        self.recover_btn.clicked.connect(self.recover_from_temp_log)
        self.clear_temp_btn.clicked.connect(self.clear_temp_log)

    # === More Methods (modularized next) ===

    def toggle_stream_mode(self):
        self.com_dropdown.setEnabled(self.com_radio.isChecked())

    def toggle_time_mode(self):
        self.timestamp_mode = "Relative" if self.relative_radio.isChecked() else "GMT"

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
                        float(parts[1])
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

    def setup_control_buttons(self, layout):
        control_box = QGroupBox("Controls")
        self.start_btn = QPushButton("Start")
        self.pause_btn = QPushButton("Pause")
        self.stop_btn = QPushButton("Stop")
        self.clear_btn = QPushButton("Clear")
        self.reset_btn = QPushButton("Reset Timer")

        self.stop_btn.setEnabled(False)
        button_layout = QHBoxLayout()
        for btn in [self.start_btn, self.pause_btn, self.stop_btn, self.clear_btn, self.reset_btn]:
            button_layout.addWidget(btn)
        control_box.setLayout(button_layout)
        layout.addWidget(control_box)

        # Connect actions
        self.start_btn.clicked.connect(self.start_stream)
        self.pause_btn.clicked.connect(self.toggle_pause)
        self.stop_btn.clicked.connect(self.stop_stream)
        self.clear_btn.clicked.connect(self.clear_plot)
        self.reset_btn.clicked.connect(self.reset_timer)

    def setup_status_labels(self, layout):
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

        self.updated_label = QLabel("Last Updated: --")
        self.updated_label.setAlignment(Qt.AlignCenter)
        self.updated_label.setStyleSheet("""
            font-size: 11px;
            font-style: italic;
            color: gray;
            margin-top: 4px;
        """)

        self.warning_label = QLabel("Please export CSV (if needed) and then clear the plot before restarting.")
        self.warning_label.setAlignment(Qt.AlignCenter)
        self.warning_label.setStyleSheet("font-size: 11px; font-style: italic; color: red;")
        self.warning_label.hide()

        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(15)
        stats_layout.addStretch()
        stats_layout.addWidget(self.min_label)
        stats_layout.addWidget(self.max_label)
        stats_layout.addWidget(self.avg_label)
        stats_layout.addStretch()

        layout.addWidget(self.warning_label)
        layout.addWidget(self.current_lux_label)
        layout.addWidget(self.adafruit_status)
        layout.addLayout(stats_layout)
        layout.addWidget(self.updated_label)

    def toggle_pause(self):
        self.paused = not self.paused
        self.pause_btn.setText("Resume" if self.paused else "Pause")

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
            selected_port = selected_label.split(" ")[0]
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
        if self.session_data:
            temp_path = os.path.join(self.logs_dir, "temp_log.csv")
            write_temp_log(temp_path, self.session_data)
        self.session_data.clear()

    def reset_timer(self):
        self.timer_start_time = time.time()
        self.clear_plot()

    def export_csv(self):
        if not self.session_data:
            QMessageBox.information(self, "No Data", "No session data to export.")
            return

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"lux_data_{timestamp}.csv"
        filepath = os.path.join(self.logs_dir, filename)

        if write_summary_csv(filepath, self.session_data):
            QMessageBox.information(self, "Export Successful", f"Data exported to:\n{filepath}")
            self.session_data.clear()
            upload_to_s3(filepath)
        else:
            QMessageBox.warning(self, "Export Failed", "Could not export data.")

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

    def read_serial(self, port):
        try:
            with serial.Serial(port, 115200, timeout=1) as ser:
                while self.running and not self.stop_event.is_set():
                    line = ser.readline().decode().strip()
                    if line:
                        self.process_data_line(line)
        except Exception as e:
            print(f"[Serial] Error: {e}")

    def read_mqtt(self):
        if self.mqtt_client is not None and self.mqtt_thread and self.mqtt_thread.is_alive():
            return

        def on_connect(client, userdata, flags, rc):
            client.subscribe(MQTT_TOPIC)

        def on_message(client, userdata, msg):
            try:
                payload = json.loads(msg.payload.decode())
                lux = payload.get("lux")
                if lux is not None:
                    self.append_data(lux)
                    if time.time() - self.last_aio_send_time >= AIO_SEND_INTERVAL_SEC:
                        self.last_aio_send_time = time.time()
                        Thread(target=self._send_lux_to_adafruit, args=(lux,), daemon=True).start()
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
        except Exception as e:
            print(f"[MQTT] Connection Error: {e}")

    def _send_lux_to_adafruit(self, lux):
        status = send_to_adafruit(lux)
        self.adafruit_status.setText("Adafruit IO: Updated" if status else "Adafruit IO: Error")
        self.adafruit_status.setStyleSheet("color: green;" if status else "color: red;")

    def process_data_line(self, line):
        try:
            parts = line.split(",")
            if len(parts) == 2:
                lux = float(parts[1])
                self.append_data(lux)
                if time.time() - self.last_aio_send_time >= AIO_SEND_INTERVAL_SEC:
                    self.last_aio_send_time = time.time()
                    Thread(target=self._send_lux_to_adafruit, args=(lux,), daemon=True).start()
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

        self.current_lux_label.setText(f"Current Lux: {lux:.2f}")
        self.min_label.setText(f"Min: {min(self.gmt_data):.2f}")
        self.max_label.setText(f"Max: {max(self.gmt_data):.2f}")
        self.avg_label.setText(f"Avg: {sum(self.gmt_data)/len(self.gmt_data):.2f}")
        self.updated_label.setText(f"Last Updated: {gmt_ts.strftime('%H:%M:%S')}")
        self.session_data.append((rel_ts, gmt_ts.strftime("%Y-%m-%d %H:%M:%S"), lux))

    def recover_from_temp_log(self):
        temp_path = os.path.join(self.logs_dir, "temp_log.csv")
        if not os.path.exists(temp_path):
            QMessageBox.information(self, "No Temp Log", "No temp_log.csv file found.")
            return
        try:
            self.session_data.clear()
            with open(temp_path, newline='') as f:
                reader = csv.reader(f)
                for row in reader:
                    if row and row[0].isdigit():
                        self.session_data.append((int(row[0]), row[1], float(row[2])))
            QMessageBox.information(self, "Recovery Successful", "Data recovered from temp_log.csv.")
        except Exception as e:
            QMessageBox.warning(self, "Recovery Failed", f"Could not recover data:\n{e}")

    def clear_temp_log(self):
        temp_path = os.path.join(self.logs_dir, "temp_log.csv")
        if os.path.exists(temp_path):
            os.remove(temp_path)
            QMessageBox.information(self, "Temp Log Cleared", "temp_log.csv has been deleted.")
        else:
            QMessageBox.information(self, "No Temp Log", "No temp_log.csv file to delete.")

    def closeEvent(self, event):
        if self.session_data:
            write_temp_log(os.path.join(self.logs_dir, "temp_log.csv"), self.session_data)
        self.stop_stream()
        super().closeEvent(event)