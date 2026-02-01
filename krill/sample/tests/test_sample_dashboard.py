"""
Regression tests for the Samples dashboard (SampleView at sample:sample).
Prevents TemplateSyntaxError in left_sidebar and ensures context is passed.
"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse

from ..models.sample import Sample
from ..models.aliquot import Aliquot, AliquotType
from ..models.source import Source
User = get_user_model()


class SampleDashboardViewTest(TestCase):
    """Test cases for the Samples dashboard (SampleView at sample:sample)."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
        )
        self.user.role.role = 'lab_member'
        self.user.role.save()
        self.source = Source.objects.create(name="Test Source")
        self.sample = Sample.objects.create(name="Test Sample", source=self.source)
        self.aliquot_type = AliquotType.objects.create(name="Test Type")
        self.aliquot = Aliquot.objects.create(
            sample=self.sample,
            quantity=3,
            aliquot_type=self.aliquot_type,
        )

    def test_sample_dashboard_requires_login(self):
        """Samples dashboard requires login (LoginRequiredMixin)."""
        response = self.client.get(reverse('sample:sample'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response.url or '')

    def test_sample_dashboard_returns_context_and_renders(self):
        """Samples dashboard returns 200 with sample_count, aliquot_count, etc. (regression: left_sidebar template)."""
        self.client.force_login(self.user)
        response = self.client.get(reverse('sample:sample'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'sample/sample.html')
        context = response.context
        self.assertIn('sample_count', context)
        self.assertIn('aliquot_count', context)
        self.assertIn('aliquot_type_count', context)
        self.assertIn('source_count', context)
        self.assertEqual(context['sample_count'], 1)
        self.assertEqual(context['aliquot_count'], 1)
        self.assertEqual(context['aliquot_type_count'], 1)
        self.assertEqual(context['source_count'], 1)
