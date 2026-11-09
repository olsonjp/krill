import re

import sentry_sdk
from django.conf import settings

# What the app receives about the caller's address, tagged on every request in Sentry.
# Sentry does not record request headers on traces, so this makes it possible to see which
# header carries the real client address behind the hosting proxy, and which can be forged.
CLIENT_IP_TAGS = {
    'ip.remote_addr': 'REMOTE_ADDR',
    'ip.do_connecting_ip': 'HTTP_DO_CONNECTING_IP',
    'ip.x_forwarded_for': 'HTTP_X_FORWARDED_FOR',
    'ip.x_real_ip': 'HTTP_X_REAL_IP',
    'ip.cf_connecting_ip': 'HTTP_CF_CONNECTING_IP',
}
MAX_TAG_LENGTH = 200  # Sentry's limit for a tag value
_UNSAFE = re.compile(r'[^\x20-\x7e]')


def _clean(value):
    """Header values come from the caller, so keep only printable ASCII and a bounded length."""
    return _UNSAFE.sub('?', value)[:MAX_TAG_LENGTH]


class ClientIPDiagnosticMiddleware:
    """Tag each request in Sentry with the client-address headers it arrived with.

    Diagnostic only: it changes nothing about the request. Turn it off without a code change
    by setting SENTRY_CLIENT_IP_TAGS=false.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if getattr(settings, 'SENTRY_CLIENT_IP_TAGS', False) and sentry_sdk.get_client().is_active():
            for tag, meta_key in CLIENT_IP_TAGS.items():
                value = request.META.get(meta_key)
                if value:
                    sentry_sdk.set_tag(tag, _clean(value))
        return self.get_response(request)
