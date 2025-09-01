from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from person.models import UserRole
from ..models.sample import Sample
from ..models.aliquot import Aliquot, AliquotType
from ..models.source import Source

User = get_user_model()


class AccessLevelTestCase(TestCase):
    def setUp(self):
        """Set up test data"""
        # Create users with different roles
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123'
        )
        self.manager_user = User.objects.create_user(
            username='manager',
            email='manager@test.com',
            password='testpass123'
        )
        self.member_user = User.objects.create_user(
            username='member',
            email='member@test.com',
            password='testpass123'
        )
        self.viewer_user = User.objects.create_user(
            username='viewer',
            email='viewer@test.com',
            password='testpass123'
        )
        
        # Create user roles using get_or_create
        self.admin_role, _ = UserRole.objects.get_or_create(
            user=self.admin_user,
            defaults={'role': 'lab_admin'}
        )
        self.admin_role.role = 'lab_admin'
        self.admin_role.save()
        
        self.manager_role, _ = UserRole.objects.get_or_create(
            user=self.manager_user,
            defaults={'role': 'lab_manager'}
        )
        self.manager_role.role = 'lab_manager'
        self.manager_role.save()
        
        self.member_role, _ = UserRole.objects.get_or_create(
            user=self.member_user,
            defaults={'role': 'lab_member'}
        )
        self.member_role.role = 'lab_member'
        self.member_role.save()
        
        self.viewer_role, _ = UserRole.objects.get_or_create(
            user=self.viewer_user,
            defaults={'role': 'viewer'}
        )
        self.viewer_role.role = 'viewer'
        self.viewer_role.save()
        
        # Create test source
        self.source = Source.objects.create(
            name='Test Source',
            description='Test source for access level testing'
        )
        
        # Create test aliquot type
        self.aliquot_type = AliquotType.objects.create(
            name='Test Type',
            description='Test aliquot type'
        )
        
        # Create samples with different access levels
        self.admin_only_sample = Sample.objects.create(
            name='Admin Only Sample',
            source=self.source,
            access_level='admins_only'
        )
        self.manager_sample = Sample.objects.create(
            name='Manager Sample',
            source=self.source,
            access_level='admins_managers'
        )
        self.all_members_sample = Sample.objects.create(
            name='All Members Sample',
            source=self.source,
            access_level='all_members'
        )
        
        # Create aliquots with different access levels
        self.admin_only_aliquot = Aliquot.objects.create(
            sample=self.admin_only_sample,
            aliquot_type=self.aliquot_type,
            quantity=1,
            access_level='admins_only'
        )
        self.manager_aliquot = Aliquot.objects.create(
            sample=self.manager_sample,
            aliquot_type=self.aliquot_type,
            quantity=1,
            access_level='admins_managers'
        )
        self.all_members_aliquot = Aliquot.objects.create(
            sample=self.all_members_sample,
            aliquot_type=self.aliquot_type,
            quantity=1,
            access_level='all_members'
        )
        
        # Create client
        self.client = Client()

    def test_admin_access_to_all_samples(self):
        """Test that admin can access all samples"""
        self.client.login(username='admin', password='testpass123')
        
        # Test admin only sample
        response = self.client.get(
            reverse('sample:access_demo_sample', args=[self.admin_only_sample.id])
        )
        self.assertEqual(response.status_code, 200)
        
        # Test manager sample
        response = self.client.get(
            reverse('sample:access_demo_sample', args=[self.manager_sample.id])
        )
        self.assertEqual(response.status_code, 200)
        
        # Test all members sample
        response = self.client.get(
            reverse('sample:access_demo_sample', args=[self.all_members_sample.id])
        )
        self.assertEqual(response.status_code, 200)

    def test_manager_access_restrictions(self):
        """Test that manager cannot access admin-only samples"""
        self.client.login(username='manager', password='testpass123')
        
        # Test admin only sample - should be denied
        response = self.client.get(
            reverse('sample:access_demo_sample', args=[self.admin_only_sample.id])
        )
        self.assertEqual(response.status_code, 403)
        
        # Test manager sample - should be allowed
        response = self.client.get(
            reverse('sample:access_demo_sample', args=[self.manager_sample.id])
        )
        self.assertEqual(response.status_code, 200)
        
        # Test all members sample - should be allowed
        response = self.client.get(
            reverse('sample:access_demo_sample', args=[self.all_members_sample.id])
        )
        self.assertEqual(response.status_code, 200)

    def test_member_access_restrictions(self):
        """Test that member cannot access admin-only or manager samples"""
        self.client.login(username='member', password='testpass123')
        
        # Test admin only sample - should be denied
        response = self.client.get(
            reverse('sample:access_demo_sample', args=[self.admin_only_sample.id])
        )
        self.assertEqual(response.status_code, 403)
        
        # Test manager sample - should be denied
        response = self.client.get(
            reverse('sample:access_demo_sample', args=[self.manager_sample.id])
        )
        self.assertEqual(response.status_code, 403)
        
        # Test all members sample - should be allowed
        response = self.client.get(
            reverse('sample:access_demo_sample', args=[self.all_members_sample.id])
        )
        self.assertEqual(response.status_code, 200)

    def test_viewer_access_restrictions(self):
        """Test that viewer cannot access any restricted samples"""
        self.client.login(username='viewer', password='testpass123')
        
        # Test admin only sample - should be denied
        response = self.client.get(
            reverse('sample:access_demo_sample', args=[self.admin_only_sample.id])
        )
        self.assertEqual(response.status_code, 403)
        
        # Test manager sample - should be denied
        response = self.client.get(
            reverse('sample:access_demo_sample', args=[self.manager_sample.id])
        )
        self.assertEqual(response.status_code, 403)
        
        # Test all members sample - should be denied (viewers are below lab members)
        response = self.client.get(
            reverse('sample:access_demo_sample', args=[self.all_members_sample.id])
        )
        self.assertEqual(response.status_code, 403)

    def test_aliquot_access_restrictions(self):
        """Test access level restrictions for aliquots"""
        self.client.login(username='member', password='testpass123')
        
        # Test admin only aliquot - should be denied
        response = self.client.get(
            reverse('sample:access_demo_aliquot', args=[self.admin_only_aliquot.id])
        )
        self.assertEqual(response.status_code, 403)
        
        # Test manager aliquot - should be denied
        response = self.client.get(
            reverse('sample:access_demo_aliquot', args=[self.manager_aliquot.id])
        )
        self.assertEqual(response.status_code, 403)
        
        # Test all members aliquot - should be allowed
        response = self.client.get(
            reverse('sample:access_demo_aliquot', args=[self.all_members_aliquot.id])
        )
        self.assertEqual(response.status_code, 200)

    def test_access_level_info_api(self):
        """Test the access level info API endpoint"""
        self.client.login(username='admin', password='testpass123')
        
        response = self.client.get(reverse('sample:access_level_info'))
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn('user_role', data)
        self.assertIn('sample_counts', data)
        self.assertIn('aliquot_counts', data)
        self.assertEqual(data['user_role'], 'lab_admin')

    def test_user_role_access_level_methods(self):
        """Test the UserRole access level checking methods"""
        # Test admin role
        self.assertTrue(self.admin_role.has_access_level('admins_only'))
        self.assertTrue(self.admin_role.has_access_level('admins_managers'))
        self.assertTrue(self.admin_role.has_access_level('all_members'))
        
        # Test manager role
        self.assertFalse(self.manager_role.has_access_level('admins_only'))
        self.assertTrue(self.manager_role.has_access_level('admins_managers'))
        self.assertTrue(self.manager_role.has_access_level('all_members'))
        
        # Test member role
        self.assertFalse(self.member_role.has_access_level('admins_only'))
        self.assertFalse(self.member_role.has_access_level('admins_managers'))
        self.assertTrue(self.member_role.has_access_level('all_members'))
        
        # Test viewer role
        self.assertFalse(self.viewer_role.has_access_level('admins_only'))
        self.assertFalse(self.viewer_role.has_access_level('admins_managers'))
        self.assertFalse(self.viewer_role.has_access_level('all_members'))

    def test_can_access_object_method(self):
        """Test the can_access_object method"""
        # Test admin can access all objects
        self.assertTrue(self.admin_role.can_access_object(self.admin_only_sample))
        self.assertTrue(self.admin_role.can_access_object(self.manager_sample))
        self.assertTrue(self.admin_role.can_access_object(self.all_members_sample))
        
        # Test manager access restrictions
        self.assertFalse(self.manager_role.can_access_object(self.admin_only_sample))
        self.assertTrue(self.manager_role.can_access_object(self.manager_sample))
        self.assertTrue(self.manager_role.can_access_object(self.all_members_sample))
        
        # Test member access restrictions
        self.assertFalse(self.member_role.can_access_object(self.admin_only_sample))
        self.assertFalse(self.member_role.can_access_object(self.manager_sample))
        self.assertTrue(self.member_role.can_access_object(self.all_members_sample))
