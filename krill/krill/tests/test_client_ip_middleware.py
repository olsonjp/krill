from unittest import mock

import sentry_sdk
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase, override_settings

from krill.middleware import MAX_TAG_LENGTH, ClientIPDiagnosticMiddleware


def make_middleware(view=None):
    return ClientIPDiagnosticMiddleware(view or (lambda request: HttpResponse('ok')))


class ClientIPDiagnosticMiddlewareTest(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def run_request(self, **meta):
        """Run a request through the middleware and return the tags it set."""
        tags = {}
        with override_settings(SENTRY_CLIENT_IP_TAGS=True), \
                mock.patch('krill.middleware.sentry_sdk.get_client') as get_client, \
                mock.patch('krill.middleware.sentry_sdk.set_tag', side_effect=tags.__setitem__):
            get_client.return_value.is_active.return_value = True
            response = make_middleware()(self.factory.get('/health/', **meta))
        self.assertEqual(response.status_code, 200)
        return tags

    def test_tags_the_client_address_headers_it_receives(self):
        tags = self.run_request(
            REMOTE_ADDR='10.1.2.3',
            HTTP_DO_CONNECTING_IP='198.51.100.7',
            HTTP_X_FORWARDED_FOR='203.0.113.7, 198.51.100.7',
            HTTP_X_REAL_IP='203.0.113.8',
            HTTP_CF_CONNECTING_IP='203.0.113.9',
        )
        self.assertEqual(tags, {
            'ip.remote_addr': '10.1.2.3',
            'ip.do_connecting_ip': '198.51.100.7',
            'ip.x_forwarded_for': '203.0.113.7, 198.51.100.7',
            'ip.x_real_ip': '203.0.113.8',
            'ip.cf_connecting_ip': '203.0.113.9',
        })

    def test_headers_that_are_absent_are_not_tagged(self):
        tags = self.run_request(HTTP_DO_CONNECTING_IP='198.51.100.7')
        self.assertIn('ip.do_connecting_ip', tags)
        self.assertNotIn('ip.x_forwarded_for', tags)
        self.assertNotIn('ip.cf_connecting_ip', tags)

    def test_values_from_the_caller_are_bounded_and_printable(self):
        tags = self.run_request(HTTP_X_FORWARDED_FOR='1.2.3.4\r\n\x00' + 'a' * 500)
        value = tags['ip.x_forwarded_for']
        self.assertLessEqual(len(value), MAX_TAG_LENGTH)
        self.assertTrue(value.startswith('1.2.3.4???'))
        self.assertTrue(all(32 <= ord(c) < 127 for c in value))

    def test_does_nothing_when_switched_off(self):
        with override_settings(SENTRY_CLIENT_IP_TAGS=False), \
                mock.patch('krill.middleware.sentry_sdk.set_tag') as set_tag:
            make_middleware()(self.factory.get('/', HTTP_DO_CONNECTING_IP='198.51.100.7'))
        set_tag.assert_not_called()

    def test_does_nothing_when_sentry_is_not_active(self):
        with override_settings(SENTRY_CLIENT_IP_TAGS=True), \
                mock.patch('krill.middleware.sentry_sdk.get_client') as get_client, \
                mock.patch('krill.middleware.sentry_sdk.set_tag') as set_tag:
            get_client.return_value.is_active.return_value = False
            make_middleware()(self.factory.get('/', HTTP_DO_CONNECTING_IP='198.51.100.7'))
        set_tag.assert_not_called()

    def test_request_and_response_are_untouched(self):
        seen = {}

        def view(request):
            seen['xff'] = request.META.get('HTTP_X_FORWARDED_FOR')
            return HttpResponse('body', status=201)

        with override_settings(SENTRY_CLIENT_IP_TAGS=True):
            response = make_middleware(view)(self.factory.get('/', HTTP_X_FORWARDED_FOR='203.0.113.7'))
        self.assertEqual((response.status_code, response.content), (201, b'body'))
        self.assertEqual(seen['xff'], '203.0.113.7')


class ClientIPDiagnosticWithRealSentryTest(SimpleTestCase):
    """With the real SDK, the tags end up on the events Sentry would send."""

    def test_captured_events_carry_the_tags(self):
        events = []
        sentry_sdk.init(dsn='https://key@example.invalid/1', before_send=lambda event, hint: events.append(event))
        self.addCleanup(sentry_sdk.init)   # back to an inactive client

        def view(request):
            sentry_sdk.capture_message('probe')
            return HttpResponse('ok')

        with override_settings(SENTRY_CLIENT_IP_TAGS=True):
            make_middleware(view)(RequestFactory().get(
                '/health/', HTTP_DO_CONNECTING_IP='198.51.100.7', HTTP_X_FORWARDED_FOR='203.0.113.7'))
        self.assertEqual(len(events), 1)
        tags = events[0]['tags']
        self.assertEqual(tags['ip.do_connecting_ip'], '198.51.100.7')
        self.assertEqual(tags['ip.x_forwarded_for'], '203.0.113.7')
