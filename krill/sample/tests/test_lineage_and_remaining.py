import datetime

from django.urls import reverse

from ..models.aliquot import Aliquot, AliquotDisposition, AliquotType
from ..models.sample import Sample
from .test_views import SampleViewTest


class CreateChildAliquotTest(SampleViewTest):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.user)
        self.create_url = reverse('sample:sample_create')

    def test_create_form_prefills_parent_and_sample(self):
        response = self.client.get(self.create_url, {'type': 'aliquot', 'parent': self.aliquot.id})
        form = response.context['form']
        self.assertEqual(form.initial['parent'], self.aliquot.id)
        self.assertEqual(form.initial['sample'], self.sample.id)
        self.assertContains(response, f'<option value="{self.aliquot.id}" selected>')

    def test_create_form_ignores_bad_parent(self):
        for bad in ('abc', '99999', ''):
            with self.subTest(parent=bad):
                response = self.client.get(self.create_url, {'type': 'aliquot', 'parent': bad})
                self.assertEqual(response.status_code, 200)
                self.assertNotIn('parent', response.context['form'].initial)

    def test_parent_param_ignored_for_other_types(self):
        response = self.client.get(self.create_url, {'type': 'source', 'parent': self.aliquot.id})
        self.assertEqual(response.status_code, 200)

    def test_posting_prefilled_form_creates_child_of_original(self):
        response = self.client.post(
            self.create_url + f'?type=aliquot&parent={self.aliquot.id}',
            {
                'parent': self.aliquot.id,
                'sample': self.sample.id,
                'aliquot_type': self.aliquot_type.id,
                'disposition': self.stored_disposition.id,
                'access_level': 'all_members',
                'count': 1,
            },
        )
        self.assertEqual(response.status_code, 302)
        child = Aliquot.objects.get(parent=self.aliquot)
        self.assertEqual(child.sample, self.sample)
        self.assertIn(child, self.aliquot.children.all())

    def test_both_aliquot_pages_have_create_child_button(self):
        expected = f'{reverse("sample:sample_create")}?type=aliquot&amp;parent={self.aliquot.id}'
        for url in (
            reverse('sample:detail', kwargs={'type': 'aliquot', 'pk': self.aliquot.id}),
            reverse('sample:aliquot_detail', kwargs={'pk': self.aliquot.id}),
        ):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertContains(response, 'Create child aliquot')
                self.assertContains(response, expected.replace('&amp;', '&'))

    def test_parent_page_lists_children_and_child_page_shows_parent(self):
        child = Aliquot.objects.create(
            sample=self.sample, parent=self.aliquot, disposition=self.stored_disposition,
            aliquot_type=self.aliquot_type, passage='p3',
        )
        for url in (
            reverse('sample:detail', kwargs={'type': 'aliquot', 'pk': self.aliquot.id}),
            reverse('sample:aliquot_detail', kwargs={'pk': self.aliquot.id}),
        ):
            with self.subTest(page='parent', url=url):
                response = self.client.get(url)
                self.assertContains(response, reverse('sample:detail', kwargs={'type': 'aliquot', 'pk': child.id}))
                self.assertContains(response, 'p3')
        for url in (
            reverse('sample:detail', kwargs={'type': 'aliquot', 'pk': child.id}),
            reverse('sample:aliquot_detail', kwargs={'pk': child.id}),
        ):
            with self.subTest(page='child', url=url):
                response = self.client.get(url)
                self.assertContains(response, reverse('sample:detail', kwargs={'type': 'aliquot', 'pk': self.aliquot.id}))

    def test_aliquot_without_lineage_shows_none(self):
        response = self.client.get(reverse('sample:aliquot_detail', kwargs={'pk': self.aliquot.id}))
        self.assertContains(response, 'Lineage')
        self.assertEqual(list(response.context['children']), [])


class SampleRemainingAliquotsTest(SampleViewTest):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.user)
        self.url = reverse('sample:detail', kwargs={'type': 'sample', 'pk': self.sample.id})

    def _disp(self, name, kind):
        return AliquotDisposition.objects.get_or_create(name=name, defaults={'disposition_type': kind})[0]

    def test_lists_every_stored_aliquot_whether_or_not_it_has_a_box_position(self):
        # self.aliquot is 'stored' with no box position: it still counts as remaining
        placed = Aliquot.objects.create(
            sample=self.sample, aliquot_type=self.aliquot_type, disposition=self.stored_disposition,
            passage='p8', sample_date=datetime.date(2024, 3, 5),
        )
        placed.store_in_location(self.box, 1, 2)
        in_use = Aliquot.objects.create(sample=self.sample, disposition=self._disp('In Use', 'in_use'))
        exhausted = Aliquot.objects.create(sample=self.sample, disposition=self._disp('Used', 'exhausted'))
        disposed = Aliquot.objects.create(sample=self.sample, disposition=self._disp('Disposed', 'disposed'))
        other_sample = Sample.objects.create(name='Other', source=self.source)
        other = Aliquot.objects.create(sample=other_sample, disposition=self.stored_disposition)
        other.store_in_location(self.box, 1, 3)

        response = self.client.get(self.url)
        self.assertCountEqual(response.context['remaining_aliquots'], [placed, self.aliquot])
        self.assertEqual(response.context['remaining_count'], 2)
        self.assertContains(response, 'Remaining aliquots (2)')
        for text in ('p8', '2024-03-05', 'Test Type', 'Test Device', 'Test Box', '(1, 2)'):
            self.assertContains(response, text)
        for gone in (in_use, exhausted, disposed, other):
            self.assertNotIn(gone, response.context['remaining_aliquots'])

    def test_aliquot_without_a_position_shows_a_dash_for_its_location(self):
        response = self.client.get(self.url)
        self.assertEqual(response.context['remaining_aliquots'], [self.aliquot])
        self.assertRegex(response.content.decode(), r'<td>—</td>\s*</tr>')

    def test_soft_deleted_aliquots_are_not_remaining(self):
        self.aliquot.deleted = True
        self.aliquot.save()
        self.assertEqual(self.client.get(self.url).context['remaining_aliquots'], [])

    def test_no_stored_aliquots_shows_zero_and_message(self):
        self.aliquot.disposition = self._disp('Used', 'exhausted')
        self.aliquot.save()
        response = self.client.get(self.url)
        self.assertEqual(response.context['remaining_count'], 0)
        self.assertContains(response, 'Remaining aliquots (0)')
        self.assertContains(response, 'No aliquots of this sample are currently stored.')

    def test_link_goes_to_aliquot_list_filtered_to_sample(self):
        response = self.client.get(self.url)
        self.assertContains(response, f'{reverse("sample:sample_list")}?type=aliquot&sample={self.sample.id}')

    def test_other_detail_pages_have_no_remaining_section(self):
        response = self.client.get(reverse('sample:detail', kwargs={'type': 'source', 'pk': self.source.id}))
        self.assertNotContains(response, 'Remaining aliquots')


class AliquotListSampleFilterTest(SampleViewTest):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.user)
        self.other_sample = Sample.objects.create(name='Test Sample 2', source=self.source)
        self.other = Aliquot.objects.create(sample=self.other_sample, disposition=self.stored_disposition)

    def _list(self, **params):
        return self.client.get(reverse('sample:sample_list'), {'type': 'aliquot', **params})

    def test_sample_filter_is_exact(self):
        # 'Test Sample' is a substring of 'Test Sample 2'; the id filter must not mix them up
        items = self._list(sample=self.sample.id).context['items']
        self.assertEqual(list(items), [self.aliquot])

    def test_sample_filter_shows_chip_and_survives_the_search_form(self):
        response = self._list(sample=self.sample.id)
        self.assertEqual(response.context['sample_filter'], self.sample)
        self.assertContains(response, 'Sample: Test Sample')
        self.assertContains(response, f'name="sample" value="{self.sample.id}"')

    def test_bad_sample_filter_is_ignored(self):
        for bad in ('abc', '99999'):
            with self.subTest(sample=bad):
                response = self._list(sample=bad)
                self.assertEqual(response.status_code, 200)
                self.assertIsNone(response.context['sample_filter'])
        self.assertEqual(len(self._list(sample='abc').context['items']), 2)
