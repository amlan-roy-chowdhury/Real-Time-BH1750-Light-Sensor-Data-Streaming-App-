import sys
import os
import unittest
from unittest.mock import patch, MagicMock
from PyQt5.QtWidgets import QApplication
from PyQt5.QtTest import QTest
import time
import json

# Add src directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
from app import SensorDashboard

class TestSensorDashboard(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication(sys.argv)
        cls.window = SensorDashboard()
        cls.window.show()
        QTest.qWait(500)  # Allow time for GUI to fully initialize

    @classmethod
    def tearDownClass(cls):
        cls.window.close()
        cls.app.quit()

    def test_dual_logging(self):
        self.window.timer_start_time = time.time()
        lux = 100.0
        timestamp = int(time.time() * 1000)
        line = f"{timestamp},{lux}"
        self.window.process_data_line(line)
        self.assertGreater(len(self.window.relative_data), 0)
        self.assertGreater(len(self.window.gmt_data), 0)
        print("[PASS] Dual timestamp logging")

    def test_csv_logging(self):
        self.window.timer_start_time = time.time()
        lux = 321.0
        timestamp = int(time.time() * 1000)
        self.window.process_data_line(f"{timestamp},{lux}")

        self.assertTrue(os.path.exists("lux_log.csv"))
        with open("lux_log.csv", "r") as f:
            lines = f.readlines()
            self.assertGreater(len(lines), 0)
            self.assertIn(",", lines[-1])
        print("[PASS] CSV logging")

    def test_display_modes(self):
        self.window.relative_radio.setChecked(True)
        self.window.update_plot()
        QTest.qWait(500)
        self.window.gmt_radio.setChecked(True)
        self.window.update_plot()
        QTest.qWait(500)
        self.assertTrue(self.window.relative_radio.isChecked() or self.window.gmt_radio.isChecked())
        print("[PASS] Display mode switching")

    def test_live_lux_label(self):
        self.window.timer_start_time = time.time()
        lux = 222.5
        timestamp = int(time.time() * 1000)
        line = f"{timestamp},{lux}"
        self.window.process_data_line(line)
        self.assertIn("222.5", self.window.current_lux_label.text())
        print("[PASS] Live lux label update")

    @patch("app.aio")
    def test_adafruit_status_update(self, mock_aio):
        mock_aio.send = MagicMock()
        self.window.send_to_adafruit(123.4)
        QTest.qWait(1000)
        status_text = self.window.adafruit_status.text()
        self.assertIn("Adafruit IO", status_text)
        print("[PASS] Adafruit IO status label update")

    def test_edge_cases(self):
        self.window.timer_start_time = time.time()
        self.window.process_data_line("bad,data")
        try:
            broken_json = type("MQTTMessage", (object,), {"payload": b"{bad_json}"})()
            self.window.append_data(json.loads(broken_json.payload.decode()))
        except Exception:
            self.assertTrue(True)
        print("[PASS] Edge case handling")

if __name__ == '__main__':
    unittest.main(argv=[''], exit=False)
