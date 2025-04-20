# test/test_mqtt.py

import unittest
from unittest.mock import patch, MagicMock
from PyQt5.QtWidgets import QApplication
import sys
from ui.layout import SensorDashboard

class TestMQTT(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication(sys.argv)
        cls.window = SensorDashboard()
        cls.window.show()

    @classmethod
    def tearDownClass(cls):
        cls.window.close()
        cls.app.quit()

    @patch("core.adafruit_uploader.aio")
    def test_adafruit_status_label_update(self, mock_aio):
        mock_aio.send = MagicMock()
        self.window._send_lux_to_adafruit(200.0)
        status = self.window.adafruit_status.text()
        self.assertIn("Adafruit IO", status)

    def test_invalid_serial_line(self):
        self.window.process_data_line("invalid,data")
        self.assertTrue(True)  # Just ensure it doesn't crash

    @patch("core.adafruit_uploader.aio")
    def test_adafruit_upload_failure(self, mock_aio):
        mock_aio.send.side_effect = Exception("Simulated Failure")
        self.window._send_lux_to_adafruit(150.0)
        self.assertIn("Error", self.window.adafruit_status.text())
