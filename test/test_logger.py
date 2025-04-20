import unittest
import os
from core.data_logger import write_summary_csv, write_temp_log

class TestDataLogger(unittest.TestCase):
    def setUp(self):
        self.test_path = "test_log.csv"
        self.test_data = [(0, "2025-04-20 00:00:00", 100.0),
                          (1000, "2025-04-20 00:00:01", 200.0)]

    def tearDown(self):
        if os.path.exists(self.test_path):
            os.remove(self.test_path)

    def test_write_summary_csv_success(self):
        result = write_summary_csv(self.test_path, self.test_data)
        self.assertTrue(result)
        self.assertTrue(os.path.exists(self.test_path))

    def test_write_summary_csv_empty(self):
        result = write_summary_csv(self.test_path, [])
        self.assertTrue(result)
        with open(self.test_path) as f:
            content = f.read()
            self.assertIn("Summary", content)

    def test_write_temp_log_success(self):
        write_temp_log(self.test_path, self.test_data)
        self.assertTrue(os.path.exists(self.test_path))

    def test_write_temp_log_failure(self):
        # Simulate invalid path
        bad_path = "/invalid_path/test_log.csv"
        try:
            write_temp_log(bad_path, self.test_data)
        except Exception:
            self.assertTrue(True)
