import datetime

from django.contrib.staticfiles import finders
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from ..forms import AliquotForm, AliquotMoveForm, SampleForm
from ..models.aliquot import Aliquot, AliquotType
from ..models.sample import Sample
from ..widgets import RemoteSelect, aliquot_choice_label
from .test_views import SampleViewTest


class ComboboxFixture(SampleViewTest):
    def setUp(self):
        super().setUp()
        Aliquot.objects.all().delete()
        self.url = reverse('sample:aliquot_options')
        self.client.force_login(self.user)

    def make_aliquot(self, sample=None, **kwargs):
        return Aliquot.objects.create(
            sample=sample or self.sample, aliquot_type=kwargs.pop('aliquot_type', self.aliquot_type),
            disposition=self.stored_disposition, **kwargs)

    def search(self, q):
        return self.client.get(self.url, {'q': q}).json()


class AliquotLabelTest(ComboboxFixture):
    def test_label_has_sample_number_type_passage_and_date(self):
        a = self.make_aliquot(passage='p8', sample_date=datetime.date(2026, 3, 5))
        self.assertEqual(aliquot_choice_label(a), f'Test Sample #{a.pk} · Test Type · p8 · 2026-03-05')

    def test_label_skips_what_is_missing(self):
        a = Aliquot.objects.create(sample=self.sample, disposition=self.stored_disposition)
        self.assertEqual(aliquot_choice_label(a), f'Test Sample #{a.pk}')


class SearchEndpointTest(ComboboxFixture):
    def test_requires_login(self):
        self.client.logout()
        self.assertEqual(self.client.get(self.url, {'q': 'x'}).status_code, 302)

    def test_blank_query_returns_nothing(self):
        self.make_aliquot()
        for q in ('', '   '):
            with self.subTest(q=repr(q)):
                self.assertEqual(self.search(q), {'results': [], 'more': False})

    def test_matches_sample_name_ignoring_case(self):
        a = self.make_aliquot()
        self.make_aliquot(sample=Sample.objects.create(name='Other', source=self.source))
        self.assertEqual([r['id'] for r in self.search('test sam')['results']], [a.pk])

    def test_matches_passage_and_type(self):
        by_passage = self.make_aliquot(passage='p8')
        other_type = AliquotType.objects.create(name='Pellet')
        by_type = self.make_aliquot(aliquot_type=other_type)
        self.assertEqual([r['id'] for r in self.search('p8')['results']], [by_passage.pk])
        self.assertEqual([r['id'] for r in self.search('pellet')['results']], [by_type.pk])

    def test_every_word_must_match_so_sample_and_passage_combine(self):
        hit = self.make_aliquot(passage='p8')
        self.make_aliquot(passage='p9')
        self.make_aliquot(sample=Sample.objects.create(name='Other', source=self.source), passage='p8')
        # 'test' would also match every aliquot through its type, 'Test Type'; 'sample' is only in the name
        self.assertEqual([r['id'] for r in self.search('sample p8')['results']], [hit.pk])

    def test_aliquot_number_with_or_without_hash(self):
        target = self.make_aliquot()
        self.make_aliquot()
        for q in (str(target.pk), f'#{target.pk}'):
            with self.subTest(q=q):
                self.assertEqual(self.search(q)['results'][0]['id'], target.pk)

    def test_an_exact_number_is_listed_first_even_when_others_also_match(self):
        sample = Sample.objects.create(name='Line 7', source=self.source)   # "7" also matches this name
        many = [self.make_aliquot(sample=sample) for _ in range(25)]
        target = self.make_aliquot(sample=self.sample)
        number = str(many[3].pk)
        self.assertEqual(self.search(number)['results'][0]['id'], many[3].pk)
        self.assertNotEqual(target.pk, many[3].pk)

    def test_limit_and_more_flag(self):
        for _ in range(25):
            self.make_aliquot()
        data = self.search('test')
        self.assertEqual(len(data['results']), 20)
        self.assertTrue(data['more'])

    def test_no_more_flag_at_the_limit(self):
        for _ in range(20):
            self.make_aliquot()
        data = self.search('test')
        self.assertEqual(len(data['results']), 20)
        self.assertFalse(data['more'])

    def test_deleted_aliquots_are_not_offered(self):
        gone = self.make_aliquot()
        gone.deleted = True
        gone.save()
        self.assertEqual(self.search('test')['results'], [])

    def test_results_are_labelled_and_ordered_by_sample_then_newest(self):
        zebra = Sample.objects.create(name='Zebra', source=self.source)
        a = self.make_aliquot(sample=zebra)
        older, newer = self.make_aliquot(passage='p1'), self.make_aliquot(passage='p1')
        results = self.search('')['results'] or self.search('p1')['results']
        self.assertEqual([r['id'] for r in results], [newer.pk, older.pk])
        self.assertEqual(results[0]['label'], f'Test Sample #{newer.pk} · Test Type · p1')
        self.assertEqual(self.search('zebra')['results'][0]['id'], a.pk)

    def test_the_query_count_does_not_grow_with_the_results(self):
        self.make_aliquot()
        with CaptureQueriesContext(connection) as few:
            self.search('test')
        for _ in range(15):
            self.make_aliquot()
        with CaptureQueriesContext(connection) as many:
            self.search('test')
        self.assertEqual(len(few), len(many))


class RemoteSelectFormTest(ComboboxFixture):
    def test_the_parent_select_renders_only_a_blank_option(self):
        for _ in range(30):
            self.make_aliquot()
        html = str(AliquotForm()['parent'])
        self.assertEqual(html.count('<option'), 1)
        self.assertIn('data-search-url="%s"' % reverse('sample:aliquot_options'), html)
        self.assertIn('data-combobox', html)

    def test_a_chosen_parent_is_rendered_with_its_label(self):
        parent = self.make_aliquot(passage='p8')
        for _ in range(10):
            self.make_aliquot()
        html = str(AliquotForm(initial={'parent': parent.pk})['parent'])
        self.assertEqual(html.count('<option'), 2)
        self.assertIn(f'<option value="{parent.pk}" selected>Test Sample #{parent.pk} · Test Type · p8</option>', html)

    def test_an_edited_aliquot_shows_its_current_parent(self):
        parent = self.make_aliquot(passage='p3')
        child = self.make_aliquot(parent=parent)
        html = str(AliquotForm(instance=child)['parent'])
        self.assertIn(f'<option value="{parent.pk}" selected>', html)

    def test_any_existing_aliquot_is_accepted_when_posted(self):
        parent = self.make_aliquot()
        form = AliquotForm({'parent': parent.pk, 'sample': self.sample.pk, 'aliquot_type': self.aliquot_type.pk,
                            'disposition': self.stored_disposition.pk, 'access_level': 'all_members', 'count': 1})
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['parent'], parent)

    def test_an_unknown_aliquot_is_rejected(self):
        form = AliquotForm({'parent': 999999, 'sample': self.sample.pk, 'aliquot_type': self.aliquot_type.pk,
                            'disposition': self.stored_disposition.pk, 'access_level': 'all_members', 'count': 1})
        self.assertFalse(form.is_valid())
        self.assertIn('parent', form.errors)

    def test_rendering_the_form_does_not_load_every_aliquot(self):
        self.make_aliquot()
        with CaptureQueriesContext(connection) as few:
            str(AliquotForm()['parent'])
        for _ in range(30):
            self.make_aliquot()
        with CaptureQueriesContext(connection) as many:
            str(AliquotForm()['parent'])
        self.assertEqual(len(few), len(many))

    def test_a_non_model_field_falls_back_to_a_normal_select(self):
        from django import forms
        field = forms.ChoiceField(choices=[('a', 'A'), ('b', 'B')], widget=RemoteSelect('sample:aliquot_options'))
        self.assertEqual(field.widget.render('x', 'a').count('<option'), 2)


class MarkedFieldsTest(ComboboxFixture):
    def test_dropdowns_on_the_aliquot_form_are_marked(self):
        form = AliquotForm()
        for name in ('parent', 'sample', 'aliquot_type', 'disposition', 'lab_member', 'access_level', 'box'):
            with self.subTest(field=name):
                self.assertIn('data-combobox', str(form[name]))

    def test_only_the_parent_searches_the_server(self):
        form = AliquotForm()
        self.assertIn('data-search-url', str(form['parent']))
        for name in ('sample', 'box', 'lab_member'):
            with self.subTest(field=name):
                self.assertNotIn('data-search-url', str(form[name]))

    def test_source_on_the_sample_form_and_box_on_the_move_form_are_marked(self):
        self.assertIn('data-combobox', str(SampleForm()['source']))
        self.assertIn('data-combobox', str(AliquotMoveForm()['box']))

    def test_inputs_that_are_not_dropdowns_are_left_alone(self):
        form = AliquotForm()
        self.assertNotIn('data-combobox', str(form['passage']))
        self.assertNotIn('data-combobox', str(form['sample_date']))


class PagesTest(ComboboxFixture):
    def test_create_child_page_prefills_the_parent_and_ships_one_option(self):
        parent = self.make_aliquot(passage='p8')
        for _ in range(25):
            self.make_aliquot(passage='p1')
        response = self.client.get(reverse('sample:sample_create'), {'type': 'aliquot', 'parent': parent.pk})
        html = response.content.decode()
        self.assertIn(f'<option value="{parent.pk}" selected>Test Sample #{parent.pk} · Test Type · p8</option>', html)
        select = html[html.index('name="parent"'):]
        select = select[:select.index('</select>')]
        self.assertEqual(select.count('<option'), 2)    # blank and the chosen parent, not 26

    def test_the_layout_loads_the_script_and_the_file_exists(self):
        self.assertContains(self.client.get(reverse('home')), 'js/combobox.js')
        path = finders.find('js/combobox.js')
        self.assertIsNotNone(path)
        source = open(path).read()
        for token in ('role', 'combobox', 'aria-expanded', 'aria-activedescendant', 'aria-controls', 'listbox'):
            with self.subTest(token=token):
                self.assertIn(token, source)

    def test_the_box_clearing_script_notifies_the_combobox(self):
        html = self.client.get(reverse('sample:sample_create'), {'type': 'aliquot'}).content.decode()
        self.assertIn("field.dispatchEvent(new Event('change'", html)
