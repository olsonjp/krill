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


_IRREGULAR_SINGULARS = {'shelves': 'shelf'}


@register.filter
def singular(value):
    """'Boxes' -> 'Box', 'Shelves' -> 'Shelf', 'Aliquot Types' -> 'Aliquot Type', 'Categories' -> 'Category'.

    Only the last word changes. Chopping the final letter turns 'Boxes' into 'Boxe', so use this instead.
    """
    text = str(value or '').strip()
    if not text:
        return ''
    head, _, word = text.rpartition(' ')
    lower = word.lower()
    if lower in _IRREGULAR_SINGULARS:
        result = _IRREGULAR_SINGULARS[lower]
    elif lower.endswith('ies') and len(lower) > 3:
        result = lower[:-3] + 'y'
    elif lower.endswith(('xes', 'ches', 'shes', 'sses', 'zes')):
        result = lower[:-2]
    elif lower.endswith('s') and not lower.endswith(('ss', 'us', 'is')):
        result = lower[:-1]
    else:
        result = lower
    if word.isupper() and len(word) > 1:
        result = result.upper()
    elif word[:1].isupper():
        result = result.capitalize()
    return f'{head} {result}' if head else result
