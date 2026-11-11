from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from unittest.mock import patch, MagicMock
import json
import logging

from .models import Report, ReportTemplate
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
        with patch.object(reports_views, 'Sample', mock_sample), \
             patch.object(reports_views, 'Report', mock_report), \
             patch.object(reports_views.attention, 'summary', side_effect=Exception("Alert error")):
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
             patch.object(reports_views.attention, 'summary', side_effect=Exception("Error 4")), \
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


class ResumableAuditTest(StorageAuditReportTest):
    """Marks are saved per slot, so an audit can be left and resumed."""

    def make_audit(self, **body):
        response = self.post_audit(**dict({'sample_size': 3}, **body))
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()

    def save(self, report_id, **body):
        return self.client.post(reverse('reports:save_audit_result', args=[report_id]),
                                json.dumps(body), content_type='application/json')

    def test_generating_returns_the_url_to_resume_at(self):
        payload = self.make_audit()
        self.assertEqual(payload['url'], reverse('reports:audit_detail', args=[payload['report_id']]))

    def test_marks_are_saved_and_shown_again_when_reopened(self):
        report_id = self.make_audit()['report_id']
        response = self.save(report_id, kind='audit_slots', index=1, result='wrong', notes='box was swapped')
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()['progress'], {'total': 3, 'checked': 1, 'correct': 0, 'wrong': 1, 'complete': False})
        self.save(report_id, kind='audit_slots', index=0, result='correct', notes='')

        page = self.client.get(reverse('reports:audit_detail', args=[report_id]))
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, 'box was swapped')
        self.assertContains(page, '2 of 3')
        saved = Report.objects.get(pk=report_id).result_data['audit_slots']
        self.assertEqual([s['result'] for s in saved[:2]], ['correct', 'wrong'])

    def test_audit_is_complete_when_every_slot_is_marked(self):
        report_id = self.make_audit(include_empty_checks=True)['report_id']
        data = Report.objects.get(pk=report_id).result_data
        for key in ('audit_slots', 'empty_audit_slots'):
            for index in range(len(data[key])):
                response = self.save(report_id, kind=key, index=index, result='correct')
        self.assertTrue(response.json()['progress']['complete'])

    def test_a_mark_can_be_cleared(self):
        report_id = self.make_audit()['report_id']
        self.save(report_id, kind='audit_slots', index=0, result='correct')
        response = self.save(report_id, kind='audit_slots', index=0, result='')
        self.assertEqual(response.json()['progress']['checked'], 0)

    def test_bad_saves_are_rejected(self):
        report_id = self.make_audit()['report_id']
        for body in ({'kind': 'audit_slots', 'index': 0, 'result': 'maybe'},
                     {'kind': 'other', 'index': 0, 'result': 'correct'},
                     {'kind': 'audit_slots', 'index': 'x', 'result': 'correct'}):
            self.assertEqual(self.save(report_id, **body).status_code, 400)
        self.assertEqual(self.save(report_id, kind='audit_slots', index=99, result='correct').status_code, 404)

    def other_user(self, role='lab_member', username='other'):
        user = User.objects.create_user(username=username, password='x')
        user.role.role = role
        user.role.save()
        return user

    def test_anyone_can_view_an_audit_but_not_change_it(self):
        report_id = self.make_audit()['report_id']
        self.client.force_login(self.other_user())
        page = self.client.get(reverse('reports:audit_detail', args=[report_id]))
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, 'testuser')                       # who started it
        self.assertContains(page, 'only testuser or a lab manager can change it')
        self.assertContains(page, ' disabled')
        self.assertEqual(self.save(report_id, kind='audit_slots', index=0, result='correct').status_code, 403)
        self.client.post(reverse('reports:delete_audit', args=[report_id]))
        self.assertTrue(Report.objects.filter(pk=report_id).exists())

    def test_even_a_viewer_can_view(self):
        report_id = self.make_audit()['report_id']
        self.client.force_login(self.other_user('viewer', 'readonly'))
        self.assertEqual(self.client.get(reverse('reports:audit_detail', args=[report_id])).status_code, 200)
        self.assertEqual(self.client.get(reverse('reports:audit_list')).status_code, 200)

    def test_a_lab_manager_can_mark_and_delete_anyones_audit(self):
        report_id = self.make_audit()['report_id']
        self.client.force_login(self.other_user('lab_manager', 'pi'))
        response = self.save(report_id, kind='audit_slots', index=0, result='wrong', notes='moved')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Report.objects.get(pk=report_id).result_data['audit_slots'][0]['checked_by'], 'pi')
        self.client.post(reverse('reports:delete_audit', args=[report_id]))
        self.assertFalse(Report.objects.filter(pk=report_id).exists())

    def test_creator_can_delete_their_own_audit(self):
        report_id = self.make_audit()['report_id']
        response = self.client.post(reverse('reports:delete_audit', args=[report_id]))
        self.assertRedirects(response, reverse('reports:audit_list'))
        self.assertFalse(Report.objects.filter(pk=report_id).exists())
        self.assertEqual(self.client.get(reverse('reports:delete_audit', args=[report_id])).status_code, 405)

    def test_list_shows_everyones_audits_and_can_be_limited_to_mine(self):
        self.make_audit(name='Mine')
        other = self.other_user()
        self.client.force_login(other)
        self.client.post(reverse('reports:generate_audit_report'), json.dumps({'sample_size': 2, 'name': 'Theirs'}),
                         content_type='application/json')
        self.assertEqual(Report.objects.get(name='Theirs').created_by, other)
        everyone = self.client.get(reverse('reports:audit_list'))
        self.assertContains(everyone, 'Mine')
        self.assertContains(everyone, 'Theirs')
        only_mine = self.client.get(reverse('reports:audit_list') + '?show=mine')
        self.assertContains(only_mine, 'Theirs')          # logged in as the other user
        self.assertNotContains(only_mine, '>Mine<')

    def test_list_is_paginated(self):
        for n in range(23):
            self.make_audit(name=f'Audit {n:02d}')
        first = self.client.get(reverse('reports:audit_list'))
        self.assertEqual(len(first.context['rows']), 20)
        self.assertContains(first, 'Page 1 of 2')
        second = self.client.get(reverse('reports:audit_list') + '?page=2')
        self.assertEqual(len(second.context['rows']), 3)

    def test_audits_are_listed_on_the_form_page_to_resume(self):
        report_id = self.make_audit()['report_id']
        self.save(report_id, kind='audit_slots', index=0, result='correct')
        page = self.client.get(reverse('reports:generate_audit_report'))
        self.assertContains(page, 'Your Audits')
        self.assertContains(page, '1 of 3 checked')
        self.assertContains(page, reverse('reports:audit_detail', args=[report_id]))

    def test_report_detail_for_an_audit_opens_the_checklist(self):
        report_id = self.make_audit()['report_id']
        response = self.client.get(reverse('reports:report_detail', args=[report_id]))
        self.assertRedirects(response, reverse('reports:audit_detail', args=[report_id]))


class FailedAuditLeavesNothingBehindTest(StorageAuditReportTest):
    def test_a_failed_generation_creates_no_report(self):
        with patch.object(reports_views, 'generate_storage_audit_data', side_effect=RuntimeError('boom')):
            response = self.post_audit(sample_size=3)
        self.assertEqual(response.status_code, 500)
        self.assertEqual(Report.objects.count(), 0)

    def test_unfinished_reports_are_not_listed_as_audits(self):
        from reports.models import ReportTemplate
        template = ReportTemplate.objects.create(name='t', report_type='storage_audit', created_by=self.user)
        Report.objects.create(template=template, name='Stuck', status='pending', created_by=self.user)
        self.client.force_login(self.user)
        self.assertNotContains(self.client.get(reverse('reports:generate_audit_report')), 'Stuck')


class AuditShowsAliquotDetailsTest(StorageAuditReportTest):
    def test_checklist_shows_what_is_on_each_tube(self):
        import datetime
        from django.contrib.auth import get_user_model
        from sample.models.aliquot import AliquotType, AliquotDisposition
        AliquotLocation.objects.exclude(column=1).delete()
        aliquot = AliquotLocation.objects.get().aliquot
        aliquot.aliquot_type = AliquotType.objects.create(name='Pellet')
        aliquot.disposition = AliquotDisposition.objects.create(name='In Storage', disposition_type='stored')
        aliquot.passage = 'p8'
        aliquot.sample_date = datetime.date(2019, 11, 1)
        aliquot.lab_member_initials = 'MS'
        aliquot.save()
        self.sample.notes = 'ER+ line'
        self.sample.save()

        report_id = self.post_audit(sample_size=1).json()['report_id']
        page = self.client.get(reverse('reports:audit_detail', args=[report_id]))
        for expected in ('HeLa', 'Pellet', 'Passage p8', 'Nov 1, 2019', 'By MS',
                         f'Aliquot #{aliquot.id}', 'In Storage', 'ER+ line'):
            self.assertContains(page, expected)


class ReportsHomeTest(StorageAuditReportTest):
    """The Reports page leads with the storage audit and shows only numbers that are true."""

    def home(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('reports:reports_dashboard'))
        self.assertEqual(response.status_code, 200)
        return response

    def test_counts_audits_and_those_still_in_progress(self):
        first = self.post_audit(sample_size=2).json()['report_id']
        self.post_audit(sample_size=2)
        self.client.post(reverse('reports:save_audit_result', args=[first]),
                         json.dumps({'kind': 'audit_slots', 'index': 0, 'result': 'correct'}), content_type='application/json')
        page = self.home()
        self.assertEqual((page.context['audit_count'], page.context['audits_in_progress']), (2, 2))
        for index in (1,):
            self.client.post(reverse('reports:save_audit_result', args=[first]),
                             json.dumps({'kind': 'audit_slots', 'index': index, 'result': 'wrong'}), content_type='application/json')
        self.assertEqual(self.home().context['audits_in_progress'], 1)       # the first is now finished

    def test_recent_audits_link_to_the_checklist(self):
        report_id = self.post_audit(sample_size=2).json()['report_id']
        self.assertContains(self.home(), reverse('reports:audit_detail', args=[report_id]))

    def test_page_has_no_script_that_overwrites_the_counts_and_no_dead_report_types(self):
        page = self.home()
        self.assertNotContains(page, 'loadDashboardStats')      # it reset Total/Pending Reports to 0 every 30s
        self.assertNotContains(page, 'Pending Reports')
        self.assertNotContains(page, 'All Reports')
        self.assertContains(page, 'Start Storage Audit')

    def test_page_with_nothing_yet_explains_what_to_do(self):
        self.assertContains(self.home(), 'No audits yet')
