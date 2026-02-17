from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.http import HttpRequest

from ..models import UserRole, Permission, UserAuditLog, UserPreference
from sample.models.sample import Sample
from sample.models.source import Source

User = get_user_model()


class UserRoleModelTest(TestCase):
    """Test cases for the UserRole model"""
    def test_role_creation_and_assignment(self):
        """Test role creation and assignment"""
        user = User.objects.create_user(
            username='testuser_role',
            email='test_role@example.com',
            password='testpass123'
        )
        role, created = UserRole.objects.get_or_create(
            user=user,
            defaults={
                'role': 'lab_member',
                'department': 'Research',
                'lab_unit': 'Lab A'
            }
        )
        if not created:
            role.role = 'lab_member'
            role.department = 'Research'
            role.lab_unit = 'Lab A'
            role.save()
        self.assertEqual(role.user, user)
        self.assertEqual(role.role, 'lab_member')
        self.assertEqual(role.department, 'Research')
        self.assertEqual(role.lab_unit, 'Lab A')
        self.assertIsNotNone(role.created_at)
        self.assertIsNotNone(role.updated_at)
    def test_role_hierarchy_validation(self):
        """Test role hierarchy validation"""
        valid_roles = ['lab_admin', 'lab_manager', 'lab_member', 'viewer']
        for role_type in valid_roles:
            user = User.objects.create_user(
                username=f'user_{role_type}',
                email=f'{role_type}@example.com'
            )
            user_role, created = UserRole.objects.get_or_create(
                user=user,
                defaults={'role': role_type}
            )
            if not created:
                user_role.role = role_type
                user_role.save()
            self.assertEqual(user_role.role, role_type)
    def test_role_permission_checking(self):
        """Test role permission checking"""
        admin_user = User.objects.create_user(
            username='admin_test',
            email='admin_test@example.com'
        )
        admin_role, created = UserRole.objects.get_or_create(
            user=admin_user,
            defaults={'role': 'lab_admin'}
        )
        if not created:
            admin_role.role = 'lab_admin'
            admin_role.save()
        admin_permissions = admin_role.get_role_permissions()
        self.assertIn('sample.create', admin_permissions)
        self.assertIn('sample.delete', admin_permissions)
        self.assertIn('user.manage_permissions', admin_permissions)
        self.assertIn('system.admin', admin_permissions)
        member_user = User.objects.create_user(
            username='member_test',
            email='member_test@example.com'
        )
        member_role, created = UserRole.objects.get_or_create(
            user=member_user,
            defaults={'role': 'lab_member'}
        )
        if not created:
            member_role.role = 'lab_member'
            member_role.save()
        member_permissions = member_role.get_role_permissions()
        self.assertIn('sample.view', member_permissions)
        self.assertIn('sample.create', member_permissions)
        self.assertNotIn('sample.delete', member_permissions)
        self.assertNotIn('user.manage_permissions', member_permissions)
        viewer_user = User.objects.create_user(
            username='viewer_test',
            email='viewer_test@example.com'
        )
        viewer_role, created = UserRole.objects.get_or_create(
            user=viewer_user,
            defaults={'role': 'viewer'}
        )
        if not created:
            viewer_role.role = 'viewer'
            viewer_role.save()
        viewer_permissions = viewer_role.get_role_permissions()
        self.assertIn('sample.view', viewer_permissions)
        self.assertNotIn('sample.create', viewer_permissions)
        self.assertNotIn('sample.delete', viewer_permissions)
    def test_get_or_create_for_user_method(self):
        """Test get_or_create_for_user method"""
        user = User.objects.create_user(
            username='testuser_get_create',
            email='test_get_create@example.com',
            password='testpass123'
        )
        role = UserRole.get_or_create_for_user(user)
        self.assertEqual(role.user, user)
        self.assertEqual(role.role, 'viewer')
        existing_role = UserRole.get_or_create_for_user(user)
        self.assertEqual(existing_role, role)
        superuser = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )
        admin_role = UserRole.get_or_create_for_user(superuser)
        self.assertEqual(admin_role.role, 'lab_admin')
        staff_user = User.objects.create_user(
            username='staff',
            email='staff@example.com',
            password='staffpass123',
            is_staff=True
        )
        staff_role = UserRole.get_or_create_for_user(staff_user)
        self.assertEqual(staff_role.role, 'lab_manager')
    def test_role_string_representation(self):
        """Test role string representation"""
        string_user = User.objects.create_user(
            username='string_test',
            email='string_test@example.com'
        )
        role, created = UserRole.objects.get_or_create(
            user=string_user,
            defaults={'role': 'lab_member'}
        )
        if not created:
            role.role = 'lab_member'
            role.save()
        expected_str = f"{string_user.username} - Lab Member"
        self.assertEqual(str(role), expected_str)
    def test_role_permission_inheritance(self):
        """Test role permission inheritance"""
        admin_user = User.objects.create_user(
            username='admin_inheritance',
            email='admin_inheritance@example.com'
        )
        admin_role, created = UserRole.objects.get_or_create(
            user=admin_user,
            defaults={'role': 'lab_admin'}
        )
        if not created:
            admin_role.role = 'lab_admin'
            admin_role.save()
        admin_permissions = admin_role.get_role_permissions()
        self.assertIn('sample.view', admin_permissions)
        self.assertIn('sample.create', admin_permissions)
        self.assertIn('sample.edit', admin_permissions)
        self.assertIn('sample.delete', admin_permissions)
        self.assertIn('aliquot.view', admin_permissions)
        self.assertIn('aliquot.create', admin_permissions)
        self.assertIn('storage.view', admin_permissions)
        self.assertIn('storage.create', admin_permissions)
        self.assertIn('user.view', admin_permissions)
        self.assertIn('user.create', admin_permissions)
        self.assertIn('system.admin', admin_permissions)
    def test_has_permission_method(self):
        """Test has_permission method"""
        member_user = User.objects.create_user(
            username='member_permission',
            email='member_permission@example.com'
        )
        role, created = UserRole.objects.get_or_create(
            user=member_user,
            defaults={'role': 'lab_member'}
        )
        if not created:
            role.role = 'lab_member'
            role.save()
        self.assertTrue(role.has_permission('sample.view'))
        self.assertTrue(role.has_permission('sample.create'))
        self.assertTrue(role.has_permission('aliquot.view'))
        self.assertFalse(role.has_permission('sample.delete'))
        self.assertFalse(role.has_permission('user.manage_permissions'))
        self.assertFalse(role.has_permission('system.admin'))


class PermissionModelTest(TestCase):
    """Test cases for the Permission model"""
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.granted_by = User.objects.create_user(
            username='granter',
            email='granter@example.com',
            password='grantpass123'
        )
        self.source = Source.objects.create(name="Test Source")
        self.sample = Sample.objects.create(name="Test Sample", source=self.source)
    def test_permission_creation_and_validation(self):
        """Test permission creation and validation"""
        content_type = ContentType.objects.get_for_model(Sample)
        permission = Permission.objects.create(
            user=self.user,
            permission_type='edit',
            content_type=content_type,
            object_id=self.sample.id,
            granted_by=self.granted_by
        )
        self.assertEqual(permission.user, self.user)
        self.assertEqual(permission.permission_type, 'edit')
        self.assertEqual(permission.content_type, content_type)
        self.assertEqual(permission.object_id, self.sample.id)
        self.assertEqual(permission.granted_by, self.granted_by)
        self.assertIsNotNone(permission.granted_at)
        self.assertIsNone(permission.expires_at)
    def test_permission_expiration_handling(self):
        """Test permission expiration handling"""
        content_type = ContentType.objects.get_for_model(Sample)
        permanent_permission = Permission.objects.create(
            user=self.user,
            permission_type='view',
            content_type=content_type,
            object_id=self.sample.id
        )
        self.assertTrue(permanent_permission.is_valid())
        future_expiration = timezone.now() + timezone.timedelta(days=1)
        future_permission = Permission.objects.create(
            user=self.user,
            permission_type='edit',
            content_type=content_type,
            object_id=self.sample.id,
            expires_at=future_expiration
        )
        self.assertTrue(future_permission.is_valid())
        past_expiration = timezone.now() - timezone.timedelta(days=1)
        expired_permission = Permission.objects.create(
            user=self.user,
            permission_type='delete',
            content_type=content_type,
            object_id=self.sample.id,
            expires_at=past_expiration
        )
        self.assertFalse(expired_permission.is_valid())
    def test_permission_uniqueness_constraints(self):
        """Test permission uniqueness constraints"""
        content_type = ContentType.objects.get_for_model(Sample)
        Permission.objects.create(
            user=self.user,
            permission_type='view',
            content_type=content_type,
            object_id=self.sample.id
        )
        with self.assertRaises(IntegrityError):
            Permission.objects.create(
                user=self.user,
                permission_type='view',
                content_type=content_type,
                object_id=self.sample.id
            )
    def test_permission_validity_checking(self):
        """Test permission validity checking"""
        content_type = ContentType.objects.get_for_model(Sample)
        valid_permission = Permission.objects.create(
            user=self.user,
            permission_type='view',
            content_type=content_type,
            object_id=self.sample.id
        )
        self.assertTrue(valid_permission.is_valid())
        expired_permission = Permission.objects.create(
            user=self.user,
            permission_type='edit',
            content_type=content_type,
            object_id=self.sample.id,
            expires_at=timezone.now() - timezone.timedelta(hours=1)
        )
        self.assertFalse(expired_permission.is_valid())
    def test_permission_string_representation(self):
        """Test permission string representation"""
        content_type = ContentType.objects.get_for_model(Sample)
        permission = Permission.objects.create(
            user=self.user,
            permission_type='view',
            content_type=content_type,
            object_id=self.sample.id
        )
        expected_str = f"{self.user.username} - view - {self.sample}"
        self.assertEqual(str(permission), expected_str)


class UserAuditLogModelTest(TestCase):
    """Test cases for the UserAuditLog model"""
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.source = Source.objects.create(name="Test Source")
        self.sample = Sample.objects.create(name="Test Sample", source=self.source)
    def test_audit_log_creation(self):
        """Test audit log creation"""
        log_entry = UserAuditLog.objects.create(
            user=self.user,
            action='create',
            target_type='Sample',
            target_id=self.sample.id,
            target_name=self.sample.name,
            details={'test': 'data'}
        )
        self.assertEqual(log_entry.user, self.user)
        self.assertEqual(log_entry.action, 'create')
        self.assertEqual(log_entry.target_type, 'Sample')
        self.assertEqual(log_entry.target_id, self.sample.id)
        self.assertEqual(log_entry.target_name, self.sample.name)
        self.assertEqual(log_entry.details, {'test': 'data'})
        self.assertIsNotNone(log_entry.timestamp)
    def test_audit_log_action_tracking(self):
        """Test audit log action tracking"""
        actions = ['login', 'logout', 'create', 'update', 'delete', 'view', 'export', 'import']
        for action in actions:
            log_entry = UserAuditLog.objects.create(
                user=self.user,
                action=action,
                target_type='Sample',
                target_id=self.sample.id
            )
            self.assertEqual(log_entry.action, action)
    def test_audit_log_ip_address_capture(self):
        """Test audit log IP address capture"""
        log_entry = UserAuditLog.objects.create(
            user=self.user,
            action='login',
            ip_address='192.168.1.1'
        )
        self.assertEqual(log_entry.ip_address, '192.168.1.1')
    def test_audit_log_user_agent_capture(self):
        """Test audit log user agent capture"""
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        log_entry = UserAuditLog.objects.create(
            user=self.user,
            action='login',
            user_agent=user_agent
        )
        self.assertEqual(log_entry.user_agent, user_agent)
    def test_log_action_convenience_method(self):
        """Test log_action convenience method"""
        log_entry = UserAuditLog.log_action(
            user=self.user,
            action='create',
            target_type='Sample',
            target_id=self.sample.id,
            target_name=self.sample.name,
            details={'method': 'test'}
        )
        self.assertEqual(log_entry.user, self.user)
        self.assertEqual(log_entry.action, 'create')
        self.assertEqual(log_entry.target_type, 'Sample')
        self.assertEqual(log_entry.target_id, self.sample.id)
        self.assertEqual(log_entry.target_name, self.sample.name)
        self.assertEqual(log_entry.details, {'method': 'test'})
        self.assertIsNone(log_entry.ip_address)
        self.assertEqual(log_entry.user_agent, '')
    def test_log_action_with_request(self):
        """Test log_action with request object"""
        request = HttpRequest()
        request.META['REMOTE_ADDR'] = '192.168.1.100'
        request.META['HTTP_USER_AGENT'] = 'Test Browser/1.0'
        log_entry = UserAuditLog.log_action(
            user=self.user,
            action='login',
            request=request
        )
        self.assertEqual(log_entry.ip_address, '192.168.1.100')
        self.assertEqual(log_entry.user_agent, 'Test Browser/1.0')
    def test_get_client_ip_method(self):
        """Test get_client_ip method"""
        request = HttpRequest()
        request.META['HTTP_X_FORWARDED_FOR'] = '10.0.0.1, 192.168.1.1'
        ip = UserAuditLog.get_client_ip(request)
        self.assertEqual(ip, '10.0.0.1')
        request = HttpRequest()
        request.META['REMOTE_ADDR'] = '192.168.1.100'
        ip = UserAuditLog.get_client_ip(request)
        self.assertEqual(ip, '192.168.1.100')
    def test_audit_log_string_representation(self):
        """Test audit log string representation"""
        log_entry = UserAuditLog.objects.create(
            user=self.user,
            action='create',
            target_type='Sample'
        )
        expected_str = f"{self.user.username} - create - {log_entry.timestamp}"
        self.assertEqual(str(log_entry), expected_str)
    def test_audit_log_ordering(self):
        """Test audit log ordering by timestamp"""
        log1 = UserAuditLog.objects.create(
            user=self.user,
            action='create',
            target_type='Sample'
        )
        log2 = UserAuditLog.objects.create(
            user=self.user,
            action='update',
            target_type='Sample'
        )
        logs = UserAuditLog.objects.all()
        self.assertEqual(logs[0], log2)
        self.assertEqual(logs[1], log1)


class UserPreferenceModelTest(TestCase):
    """Test cases for the UserPreference model"""
    def setUp(self):
        """Set up test data"""
        pass
    def test_preference_creation_and_defaults(self):
        """Test preference creation and defaults"""
        pref_user = User.objects.create_user(
            username='pref_creation_test',
            email='pref_creation_test@example.com'
        )
        preference = pref_user.preference
        preference.dark_mode = True
        preference.save()
        self.assertEqual(preference.user, pref_user)
        self.assertTrue(preference.dark_mode)
        self.assertIsNotNone(preference.created_at)
        self.assertIsNotNone(preference.updated_at)
    def test_dark_mode_toggle_functionality(self):
        """Test dark mode toggle functionality"""
        toggle_user = User.objects.create_user(
            username='toggle_dark_mode_test',
            email='toggle_dark_mode_test@example.com'
        )
        preference = toggle_user.preference
        self.assertFalse(preference.dark_mode)
        preference.dark_mode = True
        preference.save()
        self.assertTrue(preference.dark_mode)
        preference.dark_mode = False
        preference.save()
        self.assertFalse(preference.dark_mode)
    def test_preference_user_relationship(self):
        """Test preference-user relationship"""
        rel_user = User.objects.create_user(
            username='pref_relationship_test',
            email='pref_relationship_test@example.com'
        )
        preference = rel_user.preference
        self.assertEqual(preference.user, rel_user)
        self.assertEqual(rel_user.preference, preference)
    def test_preference_string_representation(self):
        """Test preference string representation"""
        str_user = User.objects.create_user(
            username='pref_string_test',
            email='pref_string_test@example.com'
        )
        preference = str_user.preference
        expected_str = f"{str_user.username}'s preferences"
        self.assertEqual(str(preference), expected_str)
    def test_preference_timestamp_fields(self):
        """Test preference timestamp fields"""
        time_user = User.objects.create_user(
            username='pref_timestamp_test',
            email='pref_timestamp_test@example.com'
        )
        preference = time_user.preference
        original_created_at = preference.created_at
        original_updated_at = preference.updated_at
        preference.dark_mode = True
        preference.save()
        self.assertEqual(preference.created_at, original_created_at)
        self.assertGreater(preference.updated_at, original_updated_at)
