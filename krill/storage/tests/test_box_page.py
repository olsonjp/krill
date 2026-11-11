from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from consumables.forms import ConsumableForm, ConsumableLocationForm, ConsumableTypeForm
from consumables.models.location import ConsumableLocation, ConsumableRoom
from sample.models.aliquot import Aliquot, AliquotDisposition, AliquotLocation, AliquotType
from sample.models.sample import Sample
from sample.models.source import Source
from sample.templatetags.sample_tags import singular
from storage.forms import BoxForm, DeviceForm, RackForm, ShelfForm
from storage.models.site import Site
from storage.models.storage import Box, Device, Rack, Shelf

User = get_user_model()


class BoxFixture(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='member', password='x')
        self.client.force_login(self.user)
        self.site = Site.objects.create(name='Main')
        self.device = Device.objects.create(name='Freezer A', site=self.site)
        self.shelf = Shelf.objects.create(name='Shelf 1', device=self.device)
        self.rack = Rack.objects.create(name='Rack 1', shelf=self.shelf)
        self.source = Source.objects.create(name='Lab')
        self.stored = AliquotDisposition.objects.get_or_create(name='Stored', defaults={'disposition_type': 'stored'})[0]
        self.types = [AliquotType.objects.create(name=f'Type {i}') for i in range(3)]

    def box(self, rows=10, columns=10, name='Box'):
        return Box.objects.create(name=name, rack=self.rack, rows=rows, columns=columns)

    def fill(self, box, n):
        """Put n aliquots, each from its own sample and with a type, into the first n positions."""
        placed = []
        for index in range(n):
            sample = Sample.objects.create(name=f'Sample {box.pk}-{index}', source=self.source)
            aliquot = Aliquot.objects.create(
                sample=sample, aliquot_type=self.types[index % 3], disposition=self.stored)
            AliquotLocation.objects.create(
                aliquot=aliquot, box=box, row=index // box.columns + 1, column=index % box.columns + 1)
            placed.append(aliquot)
        return placed

    def page(self, box):
        return self.client.get(reverse('storage:detail', kwargs={'type': 'box', 'pk': box.pk}))

    def query_count(self, box):
        self.page(box)   # warm up: the first request makes one-time queries (user role, site settings)
        with CaptureQueriesContext(connection) as queries:
            response = self.page(box)
        self.assertEqual(response.status_code, 200)
        return len(queries)


class BoxPageQueryCountTest(BoxFixture):
    """Sentry PYTHON-DJANGO-37 and -38: the page must not query once per slot or per occupied slot."""

    def test_query_count_does_not_grow_with_how_full_the_box_is(self):
        few, many = self.box(name='Few'), self.box(name='Many')
        self.fill(few, 2)
        self.fill(many, 60)
        self.assertEqual(self.query_count(few), self.query_count(many))

    def test_query_count_does_not_grow_with_the_size_of_the_box(self):
        small, big = self.box(2, 2, 'Small'), self.box(10, 10, 'Big')
        self.fill(small, 2)
        self.fill(big, 2)
        self.assertEqual(self.query_count(small), self.query_count(big))

    def test_query_count_does_not_depend_on_aliquots_outside_the_box(self):
        box = self.box()
        self.fill(box, 3)
        before = self.query_count(box)
        other = self.box(name='Other')
        self.fill(other, 40)
        self.assertEqual(self.query_count(box), before)

    def test_an_empty_box_renders(self):
        self.assertEqual(self.page(self.box()).context['used_slots'], 0)


class BoxPageContentTest(BoxFixture):
    def test_the_grid_marks_occupied_and_empty_positions_with_their_aliquots(self):
        box = self.box(3, 4)
        first, second = self.fill(box, 2)
        grid = self.page(box).context['box_grid']
        self.assertEqual((len(grid), len(grid[0])), (3, 4))
        self.assertTrue(grid[0][0]['occupied'])
        self.assertEqual(grid[0][0]['aliquot'], first)
        self.assertEqual(grid[0][0]['sample'], first.sample)
        self.assertEqual(grid[0][1]['aliquot'], second)
        self.assertFalse(grid[0][2]['occupied'])
        self.assertIsNone(grid[0][2]['aliquot'])
        self.assertIsNone(grid[2][3]['sample'])
        self.assertEqual([(c['row'], c['column']) for c in grid[1]], [(2, 1), (2, 2), (2, 3), (2, 4)])

    def test_counts_and_the_location_list(self):
        box = self.box(3, 4)
        self.fill(box, 5)
        context = self.page(box).context
        self.assertEqual((context['total_slots'], context['used_slots'], context['available_slots']), (12, 5, 7))
        self.assertEqual(context['storage_percentage'], 5 / 12 * 100)
        positions = [(loc.row, loc.column) for loc in context['locations']]
        self.assertEqual(positions, sorted(positions))
        self.assertEqual(len(positions), 5)

    def test_the_page_shows_each_aliquots_type_and_disposition(self):
        box = self.box()
        self.fill(box, 3)
        response = self.page(box)
        for text in ('Type 0', 'Type 1', 'Type 2', 'Stored'):
            self.assertContains(response, text)

    def test_other_boxes_are_not_mixed_in(self):
        mine, other = self.box(name='Mine'), self.box(name='Other')
        self.fill(other, 4)
        self.assertEqual(self.page(mine).context['used_slots'], 0)


class AssignPickerTest(BoxFixture):
    def test_the_page_no_longer_lists_every_aliquot(self):
        box = self.box()
        sample = Sample.objects.create(name='Unplaced-XYZ-sample', source=self.source)
        for _ in range(30):
            Aliquot.objects.create(sample=sample, aliquot_type=self.types[0], disposition=self.stored)
        response = self.page(box)
        self.assertNotIn('available_aliquots', response.context)
        self.assertNotContains(response, 'Unplaced-XYZ-sample')

    def test_the_assign_list_is_a_search_picker_with_only_a_blank_option(self):
        html = self.page(self.box()).content.decode()
        start = html.index('id="aliquotSelect"')
        select = html[start:html.index('</select>', start)]
        self.assertIn('data-combobox="1"', select)
        self.assertIn(f'data-search-url="{reverse("sample:aliquot_options")}"', select)
        self.assertEqual(select.count('<option'), 1)

    def test_the_picker_is_emptied_each_time_the_modal_opens(self):
        html = self.page(self.box()).content.decode()
        script = html[html.index('function showAssignModal'):html.index('function closeAssignModal')]
        self.assertIn("select.value = ''", script)
        self.assertIn("dispatchEvent(new Event('change'", script)

    def test_the_modal_uses_theme_colours(self):
        html = self.page(self.box()).content.decode()
        css = html[html.index('.modal-content {'):]
        css = css[:css.index('}')]
        self.assertIn('var(--color-white)', css)
        self.assertNotIn('#fefefe', css)
        # The header, footer and fields must follow the theme too (they were hardcoded light greys)
        style = html[html.index('.modal-header {'):html.index('</style>', html.index('.modal-header {'))]
        for hardcoded in ('#f8f9fa', '#dee2e6', '#ced4da', '#6c757d', 'color: #000'):
            with self.subTest(hardcoded=hardcoded):
                self.assertNotIn(hardcoded, style)

    def test_the_modal_body_does_not_scroll_or_clip_the_picker_list(self):
        html = self.page(self.box()).content.decode()
        rule = html[html.index('.modal-body {'):]
        rule = rule[:rule.index('}')]
        self.assertIn('overflow: visible', rule)
        self.assertIn('max-height: none', rule)

    def test_assigning_still_takes_the_chosen_aliquot_id(self):
        box = self.box()
        sample = Sample.objects.create(name='Chosen', source=self.source)
        aliquot = Aliquot.objects.create(sample=sample, aliquot_type=self.types[0], disposition=self.stored)
        response = self.client.post(
            reverse('storage:assign_aliquot', kwargs={'box_id': box.pk, 'row': 2, 'column': 3}),
            {'aliquot_id': aliquot.pk})
        self.assertEqual(response.status_code, 302)
        location = AliquotLocation.objects.get(aliquot=aliquot)
        self.assertEqual((location.box, location.row, location.column), (box, 2, 3))


class StorageFormsTest(BoxFixture):
    def test_dropdowns_are_marked_for_type_to_filter(self):
        self.assertIn('data-combobox', str(DeviceForm()['site']))
        self.assertIn('data-combobox', str(ShelfForm()['device']))
        self.assertIn('data-combobox', str(RackForm()['shelf']))
        self.assertIn('data-combobox', str(BoxForm()['rack']))

    def test_shelves_and_racks_are_named_with_their_parents(self):
        other_device = Device.objects.create(name='Freezer B', site=self.site)
        Shelf.objects.create(name='Shelf 1', device=other_device)      # same name on another device
        shelf_labels = [label for value, label in RackForm().fields['shelf'].choices if str(value)]
        self.assertCountEqual(shelf_labels, ['Freezer A › Shelf 1', 'Freezer B › Shelf 1'])
        rack_labels = [label for value, label in BoxForm().fields['rack'].choices if str(value)]
        self.assertEqual(rack_labels, ['Freezer A › Shelf 1 › Rack 1'])

    def test_rendering_the_forms_does_not_query_per_option(self):
        with CaptureQueriesContext(connection) as few:
            str(BoxForm()['rack']), str(RackForm()['shelf'])
        for i in range(12):
            shelf = Shelf.objects.create(name=f'S{i}', device=self.device)
            Rack.objects.create(name=f'R{i}', shelf=shelf)
        with CaptureQueriesContext(connection) as many:
            str(BoxForm()['rack']), str(RackForm()['shelf'])
        self.assertEqual(len(few), len(many))

    def test_a_chosen_parent_is_still_accepted_when_posted(self):
        form = BoxForm({'name': 'New', 'rack': self.rack.pk, 'rows': 5, 'columns': 5})
        self.assertTrue(form.is_valid(), form.errors)


class ConsumablesFormsTest(BoxFixture):
    def test_dropdowns_are_marked_for_type_to_filter(self):
        self.assertIn('data-combobox', str(ConsumableForm()['consumable_type']))
        self.assertIn('data-combobox', str(ConsumableForm()['vendor']))
        self.assertIn('data-combobox', str(ConsumableForm()['location']))
        self.assertIn('data-combobox', str(ConsumableLocationForm()['room']))
        self.assertIn('data-combobox', str(ConsumableTypeForm()['category']))

    def test_locations_are_named_with_their_room_without_a_query_per_option(self):
        room = ConsumableRoom.objects.create(name='Cold Room')
        ConsumableLocation.objects.create(room=room, name='Cabinet B')
        def labels():
            return [label for value, label in ConsumableForm().fields['location'].choices if str(value)]
        with CaptureQueriesContext(connection) as few:
            first = labels()
        self.assertEqual(first, ['Cold Room / Cabinet B'])
        for i in range(12):
            ConsumableLocation.objects.create(room=ConsumableRoom.objects.create(name=f'Room {i}'), name='Shelf')
        with CaptureQueriesContext(connection) as many:
            self.assertEqual(len(labels()), 13)
        self.assertEqual(len(few), len(many))


class SingularFilterTest(BoxFixture):
    def test_regular_and_irregular_plurals(self):
        expected = {
            'Boxes': 'Box', 'Shelves': 'Shelf', 'Sites': 'Site', 'Devices': 'Device', 'Racks': 'Rack',
            'Aliquots': 'Aliquot', 'Aliquot Types': 'Aliquot Type', 'Sources': 'Source', 'Samples': 'Sample',
            'Consumables': 'Consumable', 'Consumable Types': 'Consumable Type', 'Vendors': 'Vendor',
            'Locations': 'Location', 'Rooms': 'Room', 'Categories': 'Category', 'Batches': 'Batch',
        }
        for plural, single in expected.items():
            with self.subTest(plural=plural):
                self.assertEqual(singular(plural), single)

    def test_case_is_kept_and_odd_input_is_safe(self):
        self.assertEqual(singular('boxes'), 'box')
        self.assertEqual(singular('BOXES'), 'BOX')
        self.assertEqual(singular(''), '')
        self.assertEqual(singular(None), '')
        self.assertEqual(singular('Status'), 'Status')       # already singular, not 'Statu'
        self.assertEqual(singular('Glass'), 'Glass')

    def _storage(self, type_, **params):
        return self.client.get(reverse('storage:storage_list'), {'type': type_, **params})

    def test_storage_lists_name_one_item_correctly(self):
        for type_, single in (('box', 'Box'), ('shelf', 'Shelf'), ('device', 'Device'), ('site', 'Site')):
            with self.subTest(type=type_):
                response = self._storage(type_)
                self.assertContains(response, f'Create New {single}')
                self.assertNotContains(response, 'Boxe<')
                self.assertNotContains(response, 'Shelve<')

    def test_no_result_text_uses_the_same_singular(self):
        for type_, single in (('box', 'box'), ('shelf', 'shelf'), ('device', 'device')):
            with self.subTest(type=type_):
                self.assertContains(self._storage(type_, q='zzzz-no-match'), f'create a new {single}.')

    def test_sample_and_consumables_lists_still_read_well(self):
        from person.models import SiteConfiguration
        config = SiteConfiguration.load()
        config.consumables_enabled = True
        config.save()
        sample_page = self.client.get(reverse('sample:sample_list'), {'type': 'aliquot-type'})
        self.assertContains(sample_page, 'Create New Aliquot Type')
        for type_, button in (('consumable', 'Add Consumable'), ('type', 'Add Consumable Type'),
                              ('vendor', 'Add Vendor'), ('location', 'Add Location')):
            with self.subTest(type=type_):
                page = self.client.get(reverse('consumables:list'), {'type': type_})
                self.assertContains(page, button)

    def test_the_count_text_uses_the_singular_for_one_result(self):
        self.box()
        self.assertContains(self._storage('box'), '1 box found')
        self.assertContains(self._storage('shelf'), '1 shelf found')

    def test_the_consumables_count_text_uses_the_singular_for_one_result(self):
        from consumables.models.consumable import Consumable
        from consumables.models.consumable_type import ConsumableType
        from person.models import SiteConfiguration
        config = SiteConfiguration.load()
        config.consumables_enabled = True
        config.save()
        Consumable.objects.create(name='Anti-GFP', consumable_type=ConsumableType.objects.create(name='Antibody', category='antibody'))
        page = self.client.get(reverse('consumables:list'), {'type': 'consumable'})
        self.assertContains(page, '1 consumable found')
