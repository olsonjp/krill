from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from unittest.mock import patch, MagicMock
import json
import logging

from .models import Report, Alert, ReportTemplate
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


class ReportListViewPageSizeTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='reportuser', password='pass')

    def test_report_list_defaults_to_50(self):
        ReportTemplate.objects.bulk_create([
            ReportTemplate(name=f"T{i}", report_type='summary', created_by=self.user)
            for i in range(10)
        ])
        templates = ReportTemplate.objects.all()
        Report.objects.bulk_create([
            Report(template=templates[i % 10], name=f"R{i}", created_by=self.user)
            for i in range(60)
        ])
        self.client.force_login(self.user)
        response = self.client.get(reverse('reports:report_list_cbv'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['reports']), 50)

    def test_report_list_grid_returns_20(self):
        ReportTemplate.objects.bulk_create([
            ReportTemplate(name=f"T{i}", report_type='summary', created_by=self.user)
            for i in range(10)
        ])
        templates = ReportTemplate.objects.all()
        Report.objects.bulk_create([
            Report(template=templates[i % 10], name=f"R{i}", created_by=self.user)
            for i in range(30)
        ])
        self.client.force_login(self.user)
        response = self.client.get(reverse('reports:report_list_cbv') + '?page_size=20')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['reports']), 20)


class AlertListViewPageSizeTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='alertuser', password='pass')

    def test_alert_list_defaults_to_50(self):
        Alert.objects.bulk_create([
            Alert(title=f"Alert{i}", message="msg", severity='low', alert_type='general')
            for i in range(60)
        ])
        self.client.force_login(self.user)
        response = self.client.get(reverse('reports:alert_list_cbv'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['alerts']), 50)

    def test_alert_list_grid_returns_20(self):
        Alert.objects.bulk_create([
            Alert(title=f"Alert{i}", message="msg", severity='low', alert_type='general')
            for i in range(30)
        ])
        self.client.force_login(self.user)
        response = self.client.get(reverse('reports:alert_list_cbv') + '?page_size=20')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['alerts']), 20)



class StorageAuditReportTest(ReportsViewTest):
    """The storage audit picks random stored aliquots and lists where to find them."""

    def setUp(self):
        super().setUp()
        from sample.models.source import Source
        from storage.models.site import Site
        from storage.models.storage import Rack, Shelf
        site = Site.objects.create(name='Main')
        device = Device.objects.create(name='Dewer', site=site)
        shelf = Shelf.objects.create(name='Canes', device=device)
        rack = Rack.objects.create(name='2', shelf=shelf)
        self.box = Box.objects.create(name='2_B', rack=rack, rows=9, columns=9)
        self.sample = Sample.objects.create(name='HeLa', source=Source.objects.create(name='Lab'))
        for column in range(1, 6):
            aliquot = Aliquot.objects.create(sample=self.sample)
            AliquotLocation.objects.create(aliquot=aliquot, box=self.box, row=1, column=column)

    def post_audit(self, **body):
        self.client.force_login(self.user)
        return self.client.post(reverse('reports:generate_audit_report'), json.dumps(body), content_type='application/json')

    def test_audit_lists_the_requested_number_of_slots_with_cane_and_box(self):
        response = self.post_audit(sample_size=3)
        self.assertEqual(response.status_code, 200, response.content)
        slots = response.json()['data']['audit_slots']
        self.assertEqual(len(slots), 3)
        for slot in slots:
            self.assertEqual((slot['device'], slot['rack'], slot['box']), ('Dewer', '2', '2_B'))
            self.assertEqual(slot['sample_name'], 'HeLa')
            self.assertEqual(slot['expected_tubes'], 1)        # one aliquot = one tube

    def test_sample_size_is_capped_at_the_number_of_stored_aliquots(self):
        data = self.post_audit(sample_size=50).json()['data']
        self.assertEqual(data['sample_size'], 5)
        self.assertEqual(len({s['location_id'] for s in data['audit_slots']}), 5)

    def test_empty_slot_checks_are_added_on_request(self):
        data = self.post_audit(sample_size=2, include_empty_checks=True).json()['data']
        self.assertEqual(len(data['empty_audit_slots']), 5)
        self.assertTrue(all(s['expected_empty'] for s in data['empty_audit_slots']))

    def test_audit_with_nothing_stored_is_not_an_error(self):
        AliquotLocation.objects.all().delete()
        response = self.post_audit(sample_size=3)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['data']['audit_slots'], [])

    def test_form_defaults_the_report_name_to_today(self):
        from django.utils import timezone
        self.client.force_login(self.user)
        response = self.client.get(reverse('reports:generate_audit_report'))
        self.assertEqual(response.status_code, 200)
        today = timezone.now().strftime('%Y-%m-%d')
        self.assertContains(response, f'value="Storage Audit - {today}"')
        self.assertNotContains(response, '2024-01-15')
