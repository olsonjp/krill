import subprocess
import sys

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

MD5 = 'django.contrib.auth.hashers.MD5PasswordHasher'


class TestPasswordHasherTest(TestCase):
    """`manage.py test` uses a fast password hasher; nothing else does (see krill/settings.py)."""

    def setUp(self):
        if sys.argv[1:2] != ['test']:
            self.skipTest('the fast hasher is only switched on by manage.py test')

    def test_the_test_command_uses_the_fast_hasher(self):
        self.assertEqual(settings.PASSWORD_HASHERS, [MD5])

    def test_users_made_in_tests_get_a_fast_hash_and_can_still_log_in(self):
        user = get_user_model().objects.create_user(username='hash-check', password='s3cret-pass')
        self.assertTrue(user.password.startswith('md5$'))
        self.assertTrue(self.client.login(username='hash-check', password='s3cret-pass'))
        self.assertFalse(self.client.login(username='hash-check', password='wrong'))

    @override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.PBKDF2PasswordHasher'])
    def test_a_test_can_still_ask_for_real_hashing(self):
        user = get_user_model().objects.create_user(username='real-hash', password='s3cret-pass')
        self.assertTrue(user.password.startswith('pbkdf2_sha256$'))


class OtherCommandsKeepTheRealHasherTest(TestCase):
    def test_other_commands_use_djangos_default_hashers(self):
        result = subprocess.run(
            [sys.executable, 'manage.py', 'shell', '-c',
             'from django.conf import settings; print("HASHERS", settings.PASSWORD_HASHERS)'],
            cwd=settings.BASE_DIR, capture_output=True, text=True, timeout=120,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        line = next(l for l in result.stdout.splitlines() if l.startswith('HASHERS'))
        self.assertIn('PBKDF2PasswordHasher', line)
        self.assertNotIn('MD5PasswordHasher', line)
