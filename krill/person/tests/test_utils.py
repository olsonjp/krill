"""
Tests for person.utils (regression tests for get_upload_temp_dir).
"""
import os
import tempfile

from django.test import TestCase, override_settings

from ..utils import get_upload_temp_dir


class GetUploadTempDirTest(TestCase):
    """Regression tests for get_upload_temp_dir."""

    def test_returns_absolute_path(self):
        """Returned path is absolute."""
        path = get_upload_temp_dir()
        self.assertTrue(os.path.isabs(path), f"Expected absolute path, got {path}")

    def test_uses_system_temp_when_setting_unset(self):
        """When FILE_UPLOAD_TEMP_DIR is not set, use system temp dir."""
        with override_settings(FILE_UPLOAD_TEMP_DIR=None):
            path = get_upload_temp_dir()
        expected = os.path.abspath(os.path.expanduser(tempfile.gettempdir()))
        self.assertEqual(path, expected)

    def test_uses_setting_when_set(self):
        """When FILE_UPLOAD_TEMP_DIR is set, use that path (resolved)."""
        custom = os.path.join(tempfile.gettempdir(), "krill_uploads")
        with override_settings(FILE_UPLOAD_TEMP_DIR=custom):
            path = get_upload_temp_dir()
        self.assertEqual(path, os.path.abspath(os.path.expanduser(custom)))

    def test_expanduser_applied(self):
        """Path with ~ is expanded."""
        with override_settings(FILE_UPLOAD_TEMP_DIR="~/krill_tmp"):
            path = get_upload_temp_dir()
        self.assertIn(os.path.expanduser("~"), path)
        self.assertTrue(os.path.isabs(path))
