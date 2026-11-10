from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.urls import reverse

from person.models import Permission
from sample.models.sample import Sample
from sample.models.source import Source

User = get_user_model()


class PermissionListTest(TestCase):
    """The list must load even when a permission points at something that no longer exists."""

    def setUp(self):
        self.admin = User.objects.create_user(username='admin2', password='x')
        self.admin.role.role = 'lab_admin'
        self.admin.role.save()
        self.member = User.objects.create_user(username='member', password='x')
        self.client.force_login(self.admin)

    def grant(self, content_type, object_id):
        return Permission.objects.create(user=self.member, permission_type='view', content_type=content_type,
                                         object_id=object_id, granted_by=self.admin)

    def page(self):
        response = self.client.get(reverse('person:permission_list'))
        self.assertEqual(response.status_code, 200)
        return response

    def test_lists_a_permission_on_an_existing_object(self):
        sample = Sample.objects.create(name='MM134', source=Source.objects.create(name='Lab'))
        self.grant(ContentType.objects.get_for_model(Sample), sample.pk)
        page = self.page()
        self.assertContains(page, 'Sample: MM134')
        self.assertContains(page, 'member')
        self.assertContains(page, 'Grant Permission')       # the page body is actually rendered

    def test_a_permission_on_a_deleted_object_still_loads(self):
        self.grant(ContentType.objects.get_for_model(Sample), 999999)
        self.assertContains(self.page(), 'Sample #999999 (no longer exists)')

    def test_a_permission_on_a_model_that_was_removed_still_loads(self):
        stale = ContentType.objects.create(app_label='sample', model='aliquottube')   # class no longer exists
        self.grant(stale, 1)
        self.assertContains(self.page(), 'this kind of item no longer exists')

    def test_empty_list_says_so(self):
        self.assertContains(self.page(), 'No permissions have been granted.')

    def test_grant_bulk_and_revoke_pages_render_inside_the_layout(self):
        permission = self.grant(ContentType.objects.get_for_model(Sample), 999999)
        for name, args, expected in (
            ('person:grant_permission', [], 'Give a user access to one specific item.'),
            ('person:bulk_grant_permission', [], 'Give several users access'),
            ('person:revoke_permission', [permission.id], 'Remove view access from member'),
        ):
            response = self.client.get(reverse(name, args=args))
            self.assertEqual(response.status_code, 200, name)
            self.assertContains(response, expected)
            self.assertContains(response, 'class="sidebar"')       # inside the normal layout, with the menu

    def test_revoking_removes_the_permission(self):
        permission = self.grant(ContentType.objects.get_for_model(Sample), 1)
        response = self.client.post(reverse('person:revoke_permission', args=[permission.id]))
        self.assertRedirects(response, reverse('person:permission_list'))
        self.assertFalse(Permission.objects.filter(pk=permission.pk).exists())

    def test_grant_form_creates_a_permission(self):
        sample = Sample.objects.create(name='MM134', source=Source.objects.create(name='Lab'))
        response = self.client.post(reverse('person:grant_permission'), {
            'user': self.member.pk, 'permission_type': 'view',
            'content_type': ContentType.objects.get_for_model(Sample).pk, 'object_id': sample.pk,
        })
        self.assertRedirects(response, reverse('person:permission_list'))
        self.assertEqual(Permission.objects.get().object_id, sample.pk)
