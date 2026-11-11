from django.utils.http import url_has_allowed_host_and_scheme


def safe_next(request, default):
    """The ?next= / posted next= address if it stays on this site, otherwise the default."""
    candidate = request.POST.get('next') or request.GET.get('next') or ''
    if candidate and url_has_allowed_host_and_scheme(candidate, allowed_hosts={request.get_host()}):
        return candidate
    return default
