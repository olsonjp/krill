from functools import wraps
from django.http import Http404
from person.models import SiteConfiguration


class ConsumablesEnabledMixin:
    """Raises Http404 when the consumables feature is disabled."""
    def dispatch(self, request, *args, **kwargs):
        if not SiteConfiguration.load().consumables_enabled:
            raise Http404
        return super().dispatch(request, *args, **kwargs)


class ConsumablesOrderingEnabledMixin:
    """Raises Http404 when consumables ordering is disabled."""
    def dispatch(self, request, *args, **kwargs):
        config = SiteConfiguration.load()
        if not config.consumables_enabled or not config.consumables_ordering_enabled:
            raise Http404
        return super().dispatch(request, *args, **kwargs)


def consumables_enabled_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not SiteConfiguration.load().consumables_enabled:
            raise Http404
        return view_func(request, *args, **kwargs)
    return wrapper


def consumables_ordering_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        config = SiteConfiguration.load()
        if not config.consumables_enabled or not config.consumables_ordering_enabled:
            raise Http404
        return view_func(request, *args, **kwargs)
    return wrapper
