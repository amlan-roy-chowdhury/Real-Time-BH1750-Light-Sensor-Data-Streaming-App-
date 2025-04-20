# test/test_ui.py

import sys
import os
import unittest
import time
from PyQt5.QtWidgets import QApplication
from PyQt5.QtTest import QTest
from ui.layout import SensorDashboard
from unittest.mock import patch, MagicMock

class TestUI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication(sys.argv)
        cls.window = SensorDashboard()
        cls.window.show()
        QTest.qWait(500)

    @classmethod
    def tearDownClass(cls):
        cls.window.close()
        cls.app.quit()

    def test_toggle_time_mode(self):
        self.window.relative_radio.setChecked(True)
        self.window.toggle_time_mode()
        self.assertEqual(self.window.timestamp_mode, "Relative")
        self.window.gmt_radio.setChecked(True)
        self.window.toggle_time_mode()
        self.assertEqual(self.window.timestamp_mode, "GMT")

    def test_plot_toggle(self):
        self.window.relative_radio.setChecked(True)
        self.window.update_plot()
        QTest.qWait(200)
        self.window.gmt_radio.setChecked(True)
        self.window.update_plot()
        QTest.qWait(200)
        self.assertTrue(self.window.relative_radio.isChecked() or self.window.gmt_radio.isChecked())

    def test_pause_toggle(self):
        self.window.toggle_pause()
        self.assertTrue(self.window.paused)
        self.window.toggle_pause()
        self.assertFalse(self.window.paused)

    def test_warning_label_shown_on_restart(self):
        self.window.session_data = [(0, "2025-04-19 22:00:00", 50.0)]
        self.window.start_stream()
        QTest.qWait(200)
        self.window.stop_stream()
        self.assertTrue(self.window.warning_label.isVisible())
        
    @patch("serial.Serial")
    def test_start_stream_com_mode(self, mock_serial):
        self.window.com_radio.setChecked(True)
        self.window.com_dropdown.addItem("COM1")
        self.window.com_dropdown.setCurrentIndex(0)
        mock_serial.return_value.__enter__.return_value.readline.return_value = b"1000,123.4\n"
        self.window.start_stream()
        QTest.qWait(200)
        self.assertTrue(self.window.running)
        self.window.stop_stream()
