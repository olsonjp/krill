"""
Custom template tags for the sample app.
"""
from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def is_samples_list_active(context):
    """
    Return True if the "Samples" submenu item (sample list, no type filter)
    or sample detail should show as active. Used by base/left_sidebar.html
    to avoid a long inline {% if %} condition.
    """
    request = context.get('request')
    if not request:
        return False
    path = request.path
    if 'sample' not in path:
        return False
    if 'detail/aliquot/' in path or 'detail/aliquot-type/' in path or 'detail/source/' in path:
        return False
    # Active: samples list with no type filter, or sample detail page
    if 'list' in path and not request.GET.get('type'):
        return True
    if 'detail/sample/' in path:
        return True
    return False
