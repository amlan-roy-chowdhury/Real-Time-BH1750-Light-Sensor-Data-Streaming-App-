import unittest
from unittest.mock import patch
from core.s3_uploader import upload_to_s3

class TestS3Uploader(unittest.TestCase):

    @patch("core.s3_uploader.s3_client.upload_file")
    def test_upload_success(self, mock_upload):
        mock_upload.return_value = None
        upload_to_s3("dummy.csv")
        mock_upload.assert_called_once()

    @patch("core.s3_uploader.s3_client.upload_file")
    def test_upload_failure(self, mock_upload):
        mock_upload.side_effect = Exception("Simulated S3 Failure")
        upload_to_s3("dummy.csv")  # Should not raise
        self.assertTrue(True)
