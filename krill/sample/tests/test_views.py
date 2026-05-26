from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from ..models.sample import Sample
from ..models.aliquot import (
    Aliquot, AliquotType, AliquotDisposition,
    AliquotLocation,
)
from ..models.source import Source
from ..forms import SampleForm, AliquotForm, AliquotTypeForm, SourceForm
from storage.models.storage import Device, Shelf, Rack, Box
from storage.models.site import Site

User = get_user_model()


class SampleViewTest(TestCase):
    """Base test class for sample views with common setup"""
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.user_role = self.user.role
        self.user_role.role = 'lab_member'
        self.user_role.save()
        self.source = Source.objects.create(name="Test Source")
        self.sample = Sample.objects.create(
            name="Test Sample",
            source=self.source
        )
        self.aliquot_type = AliquotType.objects.create(name="Test Type")
        self.stored_disposition, _ = AliquotDisposition.objects.get_or_create(
            name='Stored',
            defaults={'disposition_type': 'stored'}
        )
        self.aliquot = Aliquot.objects.create(
            sample=self.sample,
            aliquot_type=self.aliquot_type,
            disposition=self.stored_disposition,
        )
        self.site = Site.objects.create(name="Test Site")
        self.device = Device.objects.create(name="Test Device", site=self.site)
        self.shelf = Shelf.objects.create(name="Test Shelf", device=self.device)
        self.rack = Rack.objects.create(name="Test Rack", shelf=self.shelf)
        self.box = Box.objects.create(
            name="Test Box",
            rack=self.rack,
            rows=10,
            columns=10
        )


class SampleListViewTest(SampleViewTest):
    """Test cases for the SampleListView"""
    def test_sample_list_requires_login(self):
        """Test that sample list requires login"""
        response = self.client.get(reverse('sample:sample_list'))
        self.assertEqual(response.status_code, 302)
    def test_sample_list_get_request_default(self):
        """Test sample list GET request with default type (sample)"""
        self.client.force_login(self.user)
        response = self.client.get(reverse('sample:sample_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'sample/list.html')
        self.assertIn('items', response.context)
        self.assertIn('model_name', response.context)
        self.assertEqual(response.context['model_name'], 'Samples')
        items = response.context['items']
        self.assertIn(self.sample, items)
    def test_sample_list_get_request_aliquot_type(self):
        """Test sample list GET request with aliquot type"""
        self.client.force_login(self.user)
        response = self.client.get(reverse('sample:sample_list'), {'type': 'aliquot'})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'sample/list.html')
        self.assertIn('items', response.context)
        self.assertIn('model_name', response.context)
        self.assertEqual(response.context['model_name'], 'Aliquots')
        items = response.context['items']
        self.assertIn(self.aliquot, items)
    def test_sample_list_get_request_aliquot_type_type(self):
        """Test sample list GET request with aliquot-type type"""
        self.client.force_login(self.user)
        response = self.client.get(reverse('sample:sample_list'), {'type': 'aliquot-type'})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'sample/list.html')
        self.assertIn('items', response.context)
        self.assertIn('model_name', response.context)
        self.assertEqual(response.context['model_name'], 'Aliquot Types')
        items = response.context['items']
        self.assertIn(self.aliquot_type, items)
    def test_sample_list_get_request_source_type(self):
        """Test sample list GET request with source type"""
        self.client.force_login(self.user)
        response = self.client.get(reverse('sample:sample_list'), {'type': 'source'})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'sample/list.html')
        self.assertIn('items', response.context)
        self.assertIn('model_name', response.context)
        self.assertEqual(response.context['model_name'], 'Sources')
        items = response.context['items']
        self.assertIn(self.source, items)

    def test_table_view_returns_50_items_by_default(self):
        """Table view (default) paginates at 50."""
        Source.objects.bulk_create([Source(name=f"S{i}") for i in range(60)])
        self.client.force_login(self.user)
        response = self.client.get(reverse('sample:sample_list') + '?type=source')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['items']), 50)

    def test_grid_view_returns_20_items(self):
        """Grid view (page_size=20) paginates at 20."""
        Source.objects.bulk_create([Source(name=f"S{i}") for i in range(30)])
        self.client.force_login(self.user)
        response = self.client.get(reverse('sample:sample_list') + '?type=source&page_size=20')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['items']), 20)

    def test_invalid_page_size_falls_back_to_50(self):
        """Invalid page_size values fall back to 50."""
        Source.objects.bulk_create([Source(name=f"S{i}") for i in range(60)])
        self.client.force_login(self.user)
        response = self.client.get(reverse('sample:sample_list') + '?type=source&page_size=999')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['items']), 50)

    def test_stored_disposition_badge_renders_correct_css_class(self):
        """stored disposition renders with 'stored' CSS class."""
        self.client.force_login(self.user)
        response = self.client.get(reverse('sample:sample_list') + '?type=aliquot')
        self.assertContains(response, 'status-badge stored')

    def test_in_use_disposition_badge_renders_hyphenated_css_class(self):
        """in_use disposition renders with 'in-use' CSS class, not 'in_use'."""
        in_use = AliquotDisposition.objects.create(
            name='In Use Test', disposition_type='in_use'
        )
        self.aliquot.disposition = in_use
        self.aliquot.save()
        self.client.force_login(self.user)
        response = self.client.get(reverse('sample:sample_list') + '?type=aliquot')
        self.assertContains(response, 'status-badge in-use')
        self.assertNotContains(response, 'status-badge in_use')


class ModelCreateViewTest(SampleViewTest):
    """Test cases for the ModelCreateView"""
    def test_model_create_requires_login(self):
        """Test that model create requires login"""
        response = self.client.get(reverse('sample:sample_create'))
        self.assertEqual(response.status_code, 302)
    def test_model_create_get_request_default(self):
        """Test model create GET request with default type (sample)"""
        self.client.force_login(self.user)
        response = self.client.get(reverse('sample:sample_create'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'sample/create.html')
        self.assertIn('form', response.context)
        self.assertIn('model_type', response.context)
        self.assertIn('model_name', response.context)
        self.assertEqual(response.context['model_type'], 'sample')
        self.assertEqual(response.context['model_name'], 'Sample')
        self.assertIsInstance(response.context['form'], SampleForm)
    def test_model_create_get_request_aliquot_type(self):
        """Test model create GET request with aliquot type"""
        self.client.force_login(self.user)
        response = self.client.get(reverse('sample:sample_create'), {'type': 'aliquot'})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'sample/create.html')
        self.assertIn('form', response.context)
        self.assertIn('model_type', response.context)
        self.assertIn('model_name', response.context)
        self.assertEqual(response.context['model_type'], 'aliquot')
        self.assertEqual(response.context['model_name'], 'Aliquot')
        self.assertIsInstance(response.context['form'], AliquotForm)
    def test_model_create_get_request_aliquot_type_type(self):
        """Test model create GET request with aliquot-type type"""
        self.client.force_login(self.user)
        response = self.client.get(reverse('sample:sample_create'), {'type': 'aliquot-type'})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'sample/create.html')
        self.assertIn('form', response.context)
        self.assertIn('model_type', response.context)
        self.assertIn('model_name', response.context)
        self.assertEqual(response.context['model_type'], 'aliquot-type')
        self.assertEqual(response.context['model_name'], 'Aliquot Type')
        self.assertIsInstance(response.context['form'], AliquotTypeForm)
    def test_model_create_get_request_source_type(self):
        """Test model create GET request with source type"""
        self.client.force_login(self.user)
        response = self.client.get(reverse('sample:sample_create'), {'type': 'source'})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'sample/create.html')
        self.assertIn('form', response.context)
        self.assertIn('model_type', response.context)
        self.assertIn('model_name', response.context)
        self.assertEqual(response.context['model_type'], 'source')
        self.assertEqual(response.context['model_name'], 'Source')
        self.assertIsInstance(response.context['form'], SourceForm)
    def test_model_create_post_valid_sample_data(self):
        """Test model create POST with valid sample data"""
        self.client.force_login(self.user)
        form_data = {
            'name': 'New Sample',
            'source': self.source.id,
            'notes': 'Test notes',
            'access_level': 'all_members',
        }
        response = self.client.post(reverse('sample:sample_create'), form_data)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, f"{reverse('sample:sample_list')}?type=sample")
        new_sample = Sample.objects.get(name='New Sample')
        self.assertEqual(new_sample.source, self.source)
        self.assertEqual(new_sample.notes, 'Test notes')
    def test_model_create_post_valid_aliquot_data(self):
        """Test model create POST with valid aliquot data"""
        self.client.force_login(self.user)
        form_data = {
            'sample': self.sample.id,
            'aliquot_type': self.aliquot_type.id,
            'disposition': self.stored_disposition.id,
            'access_level': 'all_members',
        }
        response = self.client.post(f"{reverse('sample:sample_create')}?type=aliquot", form_data)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, f"{reverse('sample:sample_list')}?type=aliquot")
        # A new aliquot (in addition to the one from setUp) should exist
        new_aliquots = Aliquot.objects.filter(sample=self.sample)
        self.assertTrue(new_aliquots.count() >= 1)
    def test_model_create_post_valid_aliquot_type_data(self):
        """Test model create POST with valid aliquot type data"""
        self.client.force_login(self.user)
        form_data = {
            'name': 'New Aliquot Type',
            'description': 'Test description'
        }
        response = self.client.post(f"{reverse('sample:sample_create')}?type=aliquot-type", form_data)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, f"{reverse('sample:sample_list')}?type=aliquot-type")
        new_aliquot_type = AliquotType.objects.get(name='New Aliquot Type')
        self.assertEqual(new_aliquot_type.description, 'Test description')
    def test_model_create_post_valid_source_data(self):
        """Test model create POST with valid source data"""
        self.client.force_login(self.user)
        form_data = {
            'name': 'New Source',
            'description': 'Test description'
        }
        response = self.client.post(f"{reverse('sample:sample_create')}?type=source", form_data)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, f"{reverse('sample:sample_list')}?type=source")
        new_source = Source.objects.get(name='New Source')
        self.assertEqual(new_source.description, 'Test description')
    def test_model_create_post_invalid_data(self):
        """Test model create POST with invalid data"""
        self.client.force_login(self.user)
        form_data = {
            'name': '',
            'source': self.source.id
        }
        response = self.client.post(reverse('sample:sample_create'), form_data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'sample/create.html')
        self.assertIn('form', response.context)
        self.assertFalse(response.context['form'].is_valid())


class AliquotDetailViewTest(TestCase):
    """Test cases for the AliquotDetailView"""

    def setUp(self):
        """Set up test data"""
        self.source = Source.objects.create(
            name="Test Source",
            description="A test source for samples"
        )
        self.sample = Sample.objects.create(
            name="Test Sample",
            source=self.source
        )
        self.aliquot_type = AliquotType.objects.create(
            name="Test Type",
            description="A test aliquot type"
        )
        self.stored_disposition = AliquotDisposition.objects.create(
            name="Stored",
            disposition_type="stored"
        )
        self.in_use_disposition = AliquotDisposition.objects.create(
            name="In Use",
            disposition_type="in_use"
        )
        self.exhausted_disposition = AliquotDisposition.objects.create(
            name="Exhausted",
            disposition_type="exhausted"
        )
        self.aliquot = Aliquot.objects.create(
            sample=self.sample,
            aliquot_type=self.aliquot_type,
            disposition=self.stored_disposition,
        )
        self.user = get_user_model().objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client = Client()

    def test_aliquot_detail_view_get(self):
        """Test aliquot detail view GET request"""
        self.client.force_login(self.user)
        response = self.client.get(reverse('sample:aliquot_detail', kwargs={'pk': self.aliquot.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'sample/tube_detail.html')
        self.assertIn('aliquot', response.context)
        self.assertEqual(response.context['aliquot'], self.aliquot)
        self.assertIn('form', response.context)
        self.assertIsInstance(response.context['form'], AliquotForm)

    def test_aliquot_detail_view_get_unauthenticated(self):
        """Test aliquot detail view GET request without authentication"""
        response = self.client.get(reverse('sample:aliquot_detail', kwargs={'pk': self.aliquot.pk}))
        self.assertEqual(response.status_code, 302)

    def test_aliquot_detail_view_post_valid_disposition_change(self):
        """Test aliquot detail view POST with valid disposition change"""
        self.client.force_login(self.user)
        form_data = {
            'sample': self.sample.id,
            'disposition': self.in_use_disposition.id,
            'access_level': 'all_members',
        }
        response = self.client.post(reverse('sample:aliquot_detail', kwargs={'pk': self.aliquot.pk}), form_data)
        self.assertEqual(response.status_code, 302)
        self.aliquot.refresh_from_db()
        self.assertEqual(self.aliquot.disposition, self.in_use_disposition)

    def test_aliquot_detail_view_post_stored_to_non_stored_removes_location(self):
        """Test that changing from stored to non-stored removes storage location"""
        self.client.force_login(self.user)

        site = Site.objects.create(name="Test Site", description="Test site")
        device = Device.objects.create(name="Test Device", site=site, description="Test device")
        shelf = Shelf.objects.create(name="Test Shelf", device=device, description="Test shelf")
        rack = Rack.objects.create(name="Test Rack", shelf=shelf, description="Test rack")
        box = Box.objects.create(name="Test Box", rack=rack, rows=8, columns=12, description="Test box")

        location = AliquotLocation.objects.create(
            aliquot=self.aliquot,
            box=box,
            row=1,
            column=1,
        )

        form_data = {
            'sample': self.sample.id,
            'disposition': self.in_use_disposition.id,
            'access_level': 'all_members',
        }
        response = self.client.post(reverse('sample:aliquot_detail', kwargs={'pk': self.aliquot.pk}), form_data)
        self.assertEqual(response.status_code, 302)

        self.aliquot.refresh_from_db()
        self.assertEqual(self.aliquot.disposition, self.in_use_disposition)

        self.assertFalse(AliquotLocation.objects.filter(aliquot=self.aliquot).exists())

    def test_aliquot_detail_view_context_includes_storage_location(self):
        """Test that aliquot detail view includes storage location in context"""
        self.client.force_login(self.user)

        site = Site.objects.create(name="Test Site", description="Test site")
        device = Device.objects.create(name="Test Device", site=site, description="Test device")
        shelf = Shelf.objects.create(name="Test Shelf", device=device, description="Test shelf")
        rack = Rack.objects.create(name="Test Rack", shelf=shelf, description="Test rack")
        box = Box.objects.create(name="Test Box", rack=rack, rows=8, columns=12, description="Test box")

        location = AliquotLocation.objects.create(
            aliquot=self.aliquot,
            box=box,
            row=1,
            column=1,
        )

        response = self.client.get(reverse('sample:aliquot_detail', kwargs={'pk': self.aliquot.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertIn('storage_location', response.context)
        self.assertIsNotNone(response.context['storage_location'])
        self.assertEqual(response.context['storage_location']['box'], box)
        self.assertEqual(response.context['storage_location']['row'], 1)
        self.assertEqual(response.context['storage_location']['column'], 1)

    def test_aliquot_detail_view_context_no_storage_location(self):
        """Test that aliquot detail view has no storage location when not stored"""
        self.aliquot.disposition = self.in_use_disposition
        self.aliquot.save()

        self.client.force_login(self.user)
        response = self.client.get(reverse('sample:aliquot_detail', kwargs={'pk': self.aliquot.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertIn('storage_location', response.context)
        self.assertIsNone(response.context['storage_location'])

    def test_tube_url_redirects_to_aliquot_detail(self):
        """Test that the old tube/<pk>/ URL redirects to aliquot/<pk>/"""
        self.client.force_login(self.user)
        response = self.client.get(reverse('sample:tube_detail', kwargs={'pk': self.aliquot.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertIn(f'/aliquot/{self.aliquot.pk}/', response['Location'])


class AliquotDetailViewMoveTest(TestCase):
    """Test cases for the AliquotDetailView move functionality"""

    def setUp(self):
        """Set up test data"""
        self.source = Source.objects.create(
            name="Test Source",
            description="A test source for samples"
        )
        self.sample = Sample.objects.create(
            name="Test Sample",
            source=self.source
        )
        self.aliquot_type = AliquotType.objects.create(
            name="Test Type",
            description="A test aliquot type"
        )
        self.stored_disposition = AliquotDisposition.objects.create(
            name="Stored",
            disposition_type="stored"
        )
        self.in_use_disposition = AliquotDisposition.objects.create(
            name="In Use",
            disposition_type="in_use"
        )
        self.aliquot = Aliquot.objects.create(
            sample=self.sample,
            aliquot_type=self.aliquot_type,
            disposition=self.stored_disposition,
        )

        self.site = Site.objects.create(name="Test Site", description="Test site")
        self.device = Device.objects.create(name="Test Device", site=self.site, description="Test device")
        self.shelf = Shelf.objects.create(name="Test Shelf", device=self.device, description="Test shelf")
        self.rack = Rack.objects.create(name="Test Rack", shelf=self.shelf, description="Test rack")
        self.box = Box.objects.create(name="Test Box", rack=self.rack, rows=8, columns=12, description="Test box")
        self.box2 = Box.objects.create(name="Test Box 2", rack=self.rack, rows=6, columns=8, description="Test box 2")

        self.user = get_user_model().objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client = Client()

    def test_aliquot_detail_view_get_includes_move_form(self):
        """Test that aliquot detail view includes move form in context"""
        self.client.force_login(self.user)
        response = self.client.get(reverse('sample:aliquot_detail', kwargs={'pk': self.aliquot.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertIn('move_form', response.context)
        from ..forms import AliquotMoveForm
        self.assertIsInstance(response.context['move_form'], AliquotMoveForm)

    def test_aliquot_detail_view_post_move_valid_data(self):
        """Test aliquot detail view POST with valid move data"""
        self.client.force_login(self.user)
        form_data = {
            'action': 'move',
            'box': self.box2.id,
            'row': 2,
            'column': 3
        }
        response = self.client.post(reverse('sample:aliquot_detail', kwargs={'pk': self.aliquot.pk}), form_data)
        self.assertEqual(response.status_code, 302)

        location = AliquotLocation.objects.get(aliquot=self.aliquot)
        self.assertEqual(location.box, self.box2)
        self.assertEqual(location.row, 2)
        self.assertEqual(location.column, 3)

        self.aliquot.refresh_from_db()
        self.assertEqual(self.aliquot.disposition, self.stored_disposition)

    def test_aliquot_detail_view_post_move_invalid_data(self):
        """Test aliquot detail view POST with invalid move data (exceeds max_value)"""
        self.client.force_login(self.user)
        form_data = {
            'action': 'move',
            'box': self.box.id,
            'row': 11,
            'column': 1
        }
        response = self.client.post(reverse('sample:aliquot_detail', kwargs={'pk': self.aliquot.pk}), form_data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'sample/tube_detail.html')
        self.assertIn('move_form', response.context)
        self.assertFalse(response.context['move_form'].is_valid())

    def test_aliquot_detail_view_post_move_occupied_position(self):
        """Test aliquot detail view POST with occupied position"""
        from django.contrib.messages import get_messages

        self.client.force_login(self.user)

        # Create another aliquot at (2, 3)
        other_aliquot = Aliquot.objects.create(
            sample=self.sample,
            aliquot_type=self.aliquot_type,
            disposition=self.stored_disposition,
        )
        AliquotLocation.objects.create(
            aliquot=other_aliquot,
            box=self.box2,
            row=2,
            column=3,
        )

        form_data = {
            'action': 'move',
            'box': self.box2.id,
            'row': 2,
            'column': 3
        }
        response = self.client.post(reverse('sample:aliquot_detail', kwargs={'pk': self.aliquot.pk}), form_data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'sample/tube_detail.html')
        messages_list = list(get_messages(response.wsgi_request))
        error_messages = [msg for msg in messages_list if 'occupied' in str(msg.message).lower()]
        self.assertGreater(len(error_messages), 0, "Should have error message about occupied position")

    def test_aliquot_detail_view_post_move_from_existing_location(self):
        """Test moving an aliquot from an existing location to a new one"""
        self.client.force_login(self.user)

        initial_location = AliquotLocation.objects.create(
            aliquot=self.aliquot,
            box=self.box,
            row=1,
            column=1,
        )

        form_data = {
            'action': 'move',
            'box': self.box2.id,
            'row': 3,
            'column': 4
        }
        response = self.client.post(reverse('sample:aliquot_detail', kwargs={'pk': self.aliquot.pk}), form_data)
        self.assertEqual(response.status_code, 302)

        self.assertFalse(AliquotLocation.objects.filter(id=initial_location.id).exists())

        new_location = AliquotLocation.objects.get(aliquot=self.aliquot)
        self.assertEqual(new_location.box, self.box2)
        self.assertEqual(new_location.row, 3)
        self.assertEqual(new_location.column, 4)

    def test_aliquot_detail_view_post_move_non_stored_aliquot(self):
        """Test moving an aliquot that is not in stored disposition"""
        self.aliquot.disposition = self.in_use_disposition
        self.aliquot.save()

        self.client.force_login(self.user)
        form_data = {
            'action': 'move',
            'box': self.box.id,
            'row': 1,
            'column': 1
        }
        response = self.client.post(reverse('sample:aliquot_detail', kwargs={'pk': self.aliquot.pk}), form_data)
        self.assertEqual(response.status_code, 302)

        self.aliquot.refresh_from_db()
        self.assertEqual(self.aliquot.disposition, self.stored_disposition)

        location = AliquotLocation.objects.get(aliquot=self.aliquot)
        self.assertEqual(location.box, self.box)
        self.assertEqual(location.row, 1)
        self.assertEqual(location.column, 1)

    def test_aliquot_detail_view_post_move_to_occupied_position(self):
        """Test moving an aliquot to an already occupied position"""
        from django.contrib.messages import get_messages

        # Create another aliquot at (2, 2)
        other_aliquot = Aliquot.objects.create(
            sample=self.sample,
            aliquot_type=self.aliquot_type,
            disposition=self.stored_disposition,
        )
        AliquotLocation.objects.create(
            aliquot=other_aliquot,
            box=self.box,
            row=2,
            column=2,
        )

        # Give self.aliquot its own location at (1, 1)
        AliquotLocation.objects.create(
            aliquot=self.aliquot,
            box=self.box,
            row=1,
            column=1,
        )

        self.client.force_login(self.user)
        form_data = {
            'action': 'move',
            'box': self.box.id,
            'row': 2,
            'column': 2
        }
        response = self.client.post(reverse('sample:aliquot_detail', kwargs={'pk': self.aliquot.pk}), form_data)
        self.assertEqual(response.status_code, 200)

        messages_list = list(get_messages(response.wsgi_request))
        error_messages = [msg for msg in messages_list if 'occupied' in str(msg.message).lower()]
        self.assertGreater(len(error_messages), 0, "Should have error message about occupied position")

        # Verify aliquot was not moved to occupied position
        self.assertFalse(
            AliquotLocation.objects.filter(
                aliquot=self.aliquot,
                row=2,
                column=2
            ).exists(),
            "Aliquot should not be moved to occupied position"
        )


class SampleSearchViewPageSizeTest(TestCase):
    """Test dynamic page size for the sample_search FBV."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='searchtestuser',
            email='searchtest@example.com',
            password='testpass123',
        )
        self.source = Source.objects.create(name='Search Test Source')

    def test_search_defaults_to_50(self):
        """With no page_size param, sample_search paginates at 50."""
        Sample.objects.bulk_create(
            [Sample(name=f'Sample {i}', source=self.source) for i in range(60)]
        )
        self.client.force_login(self.user)
        response = self.client.get(reverse('sample:sample_search'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['samples'].paginator.per_page, 50)

    def test_search_grid_returns_20(self):
        """With page_size=20, sample_search paginates at 20."""
        Sample.objects.bulk_create(
            [Sample(name=f'Sample {i}', source=self.source) for i in range(30)]
        )
        self.client.force_login(self.user)
        response = self.client.get(reverse('sample:sample_search') + '?page_size=20')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['samples'].paginator.per_page, 20)

    def test_invalid_page_size_falls_back_to_50(self):
        """With an unrecognised page_size value, sample_search falls back to 50."""
        Sample.objects.bulk_create(
            [Sample(name=f'Sample {i}', source=self.source) for i in range(30)]
        )
        self.client.force_login(self.user)
        response = self.client.get(reverse('sample:sample_search') + '?page_size=999')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['samples'].paginator.per_page, 50)


class AliquotSearchViewPageSizeTest(TestCase):
    """Test dynamic page size for the aliquot_search FBV."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='aliquotsearchtestuser',
            email='aliquotsearchtest@example.com',
            password='testpass123',
        )
        self.source = Source.objects.create(name='Aliquot Search Test Source')
        self.sample = Sample.objects.create(name='Aliquot Search Test Sample', source=self.source)

    def test_aliquot_search_defaults_to_50(self):
        """With no page_size param, aliquot_search paginates at 50."""
        Aliquot.objects.bulk_create(
            [Aliquot(sample=self.sample) for _ in range(60)]
        )
        self.client.force_login(self.user)
        response = self.client.get(reverse('sample:aliquot_search'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['aliquots'].paginator.per_page, 50)

    def test_aliquot_search_grid_returns_20(self):
        """With page_size=20, aliquot_search paginates at 20."""
        Aliquot.objects.bulk_create(
            [Aliquot(sample=self.sample) for _ in range(30)]
        )
        self.client.force_login(self.user)
        response = self.client.get(reverse('sample:aliquot_search') + '?page_size=20')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['aliquots'].paginator.per_page, 20)

    def test_aliquot_search_invalid_page_size_falls_back_to_50(self):
        """With an unrecognised page_size value, aliquot_search falls back to 50."""
        Aliquot.objects.bulk_create(
            [Aliquot(sample=self.sample) for _ in range(30)]
        )
        self.client.force_login(self.user)
        response = self.client.get(reverse('sample:aliquot_search') + '?page_size=999')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['aliquots'].paginator.per_page, 50)
