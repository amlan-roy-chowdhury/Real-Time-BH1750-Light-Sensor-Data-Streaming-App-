# test/test_data.py

import unittest
import sys
import time
from PyQt5.QtWidgets import QApplication
from ui.layout import SensorDashboard

class TestDataLogic(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication(sys.argv)
        cls.window = SensorDashboard()
        cls.window.show()

    @classmethod
    def tearDownClass(cls):
        cls.window.close()
        cls.app.quit()

    def test_append_data_dual_logging(self):
        lux = 123.4
        self.window.timer_start_time = time.time()
        timestamp = int(time.time() * 1000)
        self.window.process_data_line(f"{timestamp},{lux}")
        self.assertGreater(len(self.window.relative_data), 0)
        self.assertGreater(len(self.window.gmt_data), 0)

    def test_lux_display_update(self):
        lux = 456.7
        timestamp = int(time.time() * 1000)
        self.window.process_data_line(f"{timestamp},{lux}")
        self.assertIn("456.7", self.window.current_lux_label.text())

    def test_append_while_paused(self):
        self.window.paused = True
        pre_len = len(self.window.gmt_data)
        self.window.append_data(123.4)
        post_len = len(self.window.gmt_data)
        self.assertEqual(pre_len, post_len)
        self.window.paused = False  # Reset for future tests

    def test_empty_serial_line(self):
        self.window.process_data_line("")  # Should be safely ignored
        self.assertTrue(True)  # No exception = pass

    def test_serial_line_non_float(self):
        self.window.process_data_line("1000,not_a_number")  # Should not crash
        self.assertTrue(True)
