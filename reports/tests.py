from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from unittest.mock import patch, MagicMock
import json
import logging

from .models import Report, Alert
from . import views as reports_views
from sample.models import Sample, Aliquot
from sample.models.aliquot import AliquotLocation
from storage.models.storage import Device, Box
from person.models import UserAuditLog

User = get_user_model()


class ReportsViewTest(TestCase):
    """Base test class for reports views with common setup"""
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )


class DashboardStatsViewTest(ReportsViewTest):
    """Test cases for the dashboard_stats view with error handling"""

    def test_dashboard_stats_requires_login(self):
        """Test that dashboard stats requires login"""
        response = self.client.get(reverse('reports:dashboard_stats'))
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_dashboard_stats_successful_response(self):
        """Test dashboard stats returns successful response with all data"""
        self.client.force_login(self.user)
        response = self.client.get(reverse('reports:dashboard_stats'))
        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Check all expected fields are present
        expected_fields = [
            'active_samples', 'storage_usage', 'recent_reports', 'alerts',
            'total_slots', 'used_slots', 'recent_activity', 'storage_devices',
            'active_devices', 'total_aliquots', 'stored_aliquots'
        ]
        for field in expected_fields:
            self.assertIn(field, data)
            self.assertIsInstance(data[field], int)
            self.assertGreaterEqual(data[field], 0)

        # Check that _errors field is NOT present when no errors occur
        self.assertNotIn('_errors', data)

    def test_dashboard_stats_partial_failure_sample_query(self):
        """Test that dashboard stats handles failure in sample query gracefully"""
        self.client.force_login(self.user)

        mock_sample = MagicMock()
        mock_sample.objects.count.side_effect = Exception("Database connection error")
        with patch.object(reports_views, 'Sample', mock_sample):
            response = self.client.get(reverse('reports:dashboard_stats'))
            self.assertEqual(response.status_code, 200)  # Still returns 200
            data = response.json()

            # Sample count should default to 0
            self.assertEqual(data['active_samples'], 0)

            # Other fields should still be present
            self.assertIn('storage_usage', data)
            self.assertIn('recent_reports', data)

            # Errors should be tracked
            self.assertIn('_errors', data)
            self.assertIn('active_samples', str(data['_errors']))

    def test_dashboard_stats_partial_failure_storage_query(self):
        """Test that dashboard stats handles failure in storage query gracefully"""
        self.client.force_login(self.user)

        mock_box = MagicMock()
        mock_box.objects.only.side_effect = Exception("Storage query error")
        with patch.object(reports_views, 'Box', mock_box):
            response = self.client.get(reverse('reports:dashboard_stats'))
            self.assertEqual(response.status_code, 200)
            data = response.json()

            # Storage fields should default to 0
            self.assertEqual(data['total_slots'], 0)
            self.assertEqual(data['used_slots'], 0)
            self.assertEqual(data['storage_usage'], 0)

            # Other fields should still work
            self.assertIn('active_samples', data)

            # Errors should be tracked
            self.assertIn('_errors', data)

    def test_dashboard_stats_multiple_failures(self):
        """Test that dashboard stats handles multiple query failures"""
        self.client.force_login(self.user)

        mock_sample = MagicMock()
        mock_sample.objects.count.side_effect = Exception("Sample error")
        mock_report = MagicMock()
        mock_report.objects.filter.return_value.count.side_effect = Exception("Report error")
        mock_alert = MagicMock()
        mock_alert.objects.filter.return_value.count.side_effect = Exception("Alert error")
        with patch.object(reports_views, 'Sample', mock_sample), \
             patch.object(reports_views, 'Report', mock_report), \
             patch.object(reports_views, 'Alert', mock_alert):
            response = self.client.get(reverse('reports:dashboard_stats'))
            self.assertEqual(response.status_code, 200)
            data = response.json()

            # Failed queries should default to 0
            self.assertEqual(data['active_samples'], 0)
            self.assertEqual(data['recent_reports'], 0)
            self.assertEqual(data['alerts'], 0)

            # Other queries should still work
            self.assertIn('storage_devices', data)

            # Multiple errors should be tracked
            self.assertIn('_errors', data)
            self.assertEqual(len(data['_errors']), 3)

    def test_dashboard_stats_error_logging(self):
        """Test that errors are properly logged"""
        self.client.force_login(self.user)

        mock_sample = MagicMock()
        mock_sample.objects.count.side_effect = Exception("Test error")
        with patch.object(reports_views, 'logger') as mock_logger, \
             patch.object(reports_views, 'Sample', mock_sample):
            response = self.client.get(reverse('reports:dashboard_stats'))
            self.assertEqual(response.status_code, 200)

            # Verify error was logged
            mock_logger.error.assert_called()
            error_call = mock_logger.error.call_args
            self.assertIn("Error fetching active samples count", error_call[0][0])
            self.assertTrue(error_call[1]['exc_info'])  # exc_info=True was passed

    def test_dashboard_stats_warning_logging_on_errors(self):
        """Test that warning is logged when errors occur"""
        self.client.force_login(self.user)

        mock_sample = MagicMock()
        mock_sample.objects.count.side_effect = Exception("Test error")
        with patch.object(reports_views, 'logger') as mock_logger, \
             patch.object(reports_views, 'Sample', mock_sample):
            response = self.client.get(reverse('reports:dashboard_stats'))
            self.assertEqual(response.status_code, 200)

            # Verify warning was logged about errors
            mock_logger.warning.assert_called()
            warning_call = mock_logger.warning.call_args
            self.assertIn("Dashboard stats completed with", warning_call[0][0])
            self.assertIn("errors", warning_call[0][0])

    def test_dashboard_stats_all_queries_fail(self):
        """Test that dashboard stats still returns response when all queries fail"""
        self.client.force_login(self.user)

        # Mock all 7 try/except blocks to fail (view uses Device.objects.count only, not filter)
        mock_sample = MagicMock()
        mock_sample.objects.count.side_effect = Exception("Error 1")
        mock_box = MagicMock()
        mock_box.objects.only.side_effect = Exception("Error 2")
        mock_report = MagicMock()
        mock_report.objects.filter.return_value.count.side_effect = Exception("Error 3")
        mock_alert = MagicMock()
        mock_alert.objects.filter.return_value.count.side_effect = Exception("Error 4")
        mock_audit = MagicMock()
        mock_audit.objects.filter.return_value.count.side_effect = Exception("Error 5")
        mock_device = MagicMock()
        mock_device.objects.count.side_effect = Exception("Error 6")
        mock_aliquot = MagicMock()
        mock_aliquot.objects.count.side_effect = Exception("Error 7")
        mock_location = MagicMock()
        mock_location.objects.count.side_effect = Exception("Error 8")
        with patch.object(reports_views, 'Sample', mock_sample), \
             patch.object(reports_views, 'Box', mock_box), \
             patch.object(reports_views, 'Report', mock_report), \
             patch.object(reports_views, 'Alert', mock_alert), \
             patch.object(reports_views, 'UserAuditLog', mock_audit), \
             patch.object(reports_views, 'Device', mock_device), \
             patch.object(reports_views, 'Aliquot', mock_aliquot), \
             patch.object(reports_views, 'AliquotLocation', mock_location):
            response = self.client.get(reverse('reports:dashboard_stats'))
            self.assertEqual(response.status_code, 200)  # Still 200, not 500
            data = response.json()

            # All values should be 0
            self.assertEqual(data['active_samples'], 0)
            self.assertEqual(data['storage_usage'], 0)
            self.assertEqual(data['recent_reports'], 0)
            self.assertEqual(data['alerts'], 0)
            self.assertEqual(data['recent_activity'], 0)
            self.assertEqual(data['storage_devices'], 0)
            self.assertEqual(data['active_devices'], 0)
            self.assertEqual(data['total_aliquots'], 0)
            self.assertEqual(data['stored_aliquots'], 0)

            # Exactly 7 try/except blocks in the view can produce errors
            self.assertIn('_errors', data)
            self.assertEqual(len(data['_errors']), 7)

    def test_dashboard_stats_response_structure_with_errors(self):
        """Test that response structure is correct when errors occur"""
        self.client.force_login(self.user)

        mock_sample = MagicMock()
        mock_sample.objects.count.side_effect = Exception("Test error")
        with patch.object(reports_views, 'Sample', mock_sample):
            response = self.client.get(reverse('reports:dashboard_stats'))
            data = response.json()

            # All expected fields should still be present
            expected_fields = [
                'active_samples', 'storage_usage', 'recent_reports', 'alerts',
                'total_slots', 'used_slots', 'recent_activity', 'storage_devices',
                'active_devices', 'total_aliquots', 'stored_aliquots'
            ]
            for field in expected_fields:
                self.assertIn(field, data)

            # _errors field should be present
            self.assertIn('_errors', data)
            self.assertIsInstance(data['_errors'], list)
            self.assertGreater(len(data['_errors']), 0)

