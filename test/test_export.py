# test/test_export.py

import unittest
import sys
import os
import tempfile
from PyQt5.QtWidgets import QApplication
from ui.layout import SensorDashboard
from core.data_logger import write_temp_log

class TestExportAndRecovery(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication(sys.argv)
        cls.window = SensorDashboard()
        cls.window.show()

    @classmethod
    def tearDownClass(cls):
        cls.window.close()
        cls.app.quit()

    def test_temp_log_write_and_recover(self):
        self.window.session_data = [(0, "2025-04-19 22:00:00", 50.0)]
        temp_log_path = os.path.join(self.window.logs_dir, "temp_log.csv")
        if os.path.exists(temp_log_path):
            os.remove(temp_log_path)
        write_temp_log(temp_log_path, self.window.session_data)
        self.assertTrue(os.path.exists(temp_log_path))
        self.window.recover_from_temp_log()
        self.assertEqual(len(self.window.session_data), 1)

    def test_clear_temp_log(self):
        temp_log_path = os.path.join(self.window.logs_dir, "temp_log.csv")
        with open(temp_log_path, "w") as f:
            f.write("dummy data")
        self.assertTrue(os.path.exists(temp_log_path))
        self.window.clear_temp_log()
        self.assertFalse(os.path.exists(temp_log_path))

    def test_export_without_logs_dir(self):
        if os.path.exists(self.window.logs_dir):
            os.rename(self.window.logs_dir, self.window.logs_dir + "_bak")
        try:
            self.window.session_data = [(0, "2025-04-19 22:00:00", 50.0)]
            self.window.export_csv()
            self.assertTrue(True)
        finally:
            if os.path.exists(self.window.logs_dir + "_bak"):
                os.rename(self.window.logs_dir + "_bak", self.window.logs_dir)

    def test_recover_from_corrupted_temp_log(self):
        temp_path = os.path.join(self.window.logs_dir, "temp_log.csv")
        with open(temp_path, "w") as f:
            f.write("Corrupted Header\n123,XYZ\n")
        try:
            self.window.recover_from_temp_log()
            self.assertTrue(True)  # No crash
        finally:
            os.remove(temp_path)
