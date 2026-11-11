"""Form helpers for the type-to-filter dropdowns (see static/krill/js/combobox.js)."""
from django import forms
from django.urls import reverse_lazy


def aliquot_choice_label(aliquot):
    """How an aliquot is named in a picker: enough to tell similar ones apart.

    Needs aliquot.sample and aliquot.aliquot_type loaded (select_related) to avoid a query per row.
    Example: "HeLa #1234 · Cells · p8 · 2026-03-05"
    """
    parts = [f'{aliquot.sample.name} #{aliquot.pk}']
    if aliquot.aliquot_type_id:
        parts.append(aliquot.aliquot_type.name)
    if aliquot.passage:
        parts.append(aliquot.passage)
    if aliquot.sample_date:
        parts.append(f'{aliquot.sample_date:%Y-%m-%d}')
    return ' · '.join(parts)


class RemoteSelect(forms.Select):
    """A select for a very long list: it renders only its blank and current choices.

    The browser searches the rest through `search_url` (combobox.js). Validation still uses the
    field's full queryset, so any valid value that is posted is accepted. Without JavaScript the
    current value is kept but a new one cannot be chosen.
    """

    def __init__(self, search_url_name, attrs=None):
        attrs = {**(attrs or {}), 'data-combobox': '1', 'data-search-url': reverse_lazy(search_url_name)}
        super().__init__(attrs)

    def optgroups(self, name, value, attrs=None):
        iterator = self.choices
        if not hasattr(iterator, 'queryset'):          # not a model choice field: behave normally
            return super().optgroups(name, value, attrs)
        selected = [v for v in value if v not in (None, '')]
        groups = [(None, [self.create_option(name, '', '---------', False, 0, attrs=attrs)], 0)]
        if selected:
            for index, obj in enumerate(iterator.queryset.filter(pk__in=selected), start=1):
                option = self.create_option(
                    name, obj.pk, iterator.field.label_from_instance(obj), True, index, attrs=attrs)
                groups.append((None, [option], index))
        return groups


def mark_comboboxes(form):
    """Switch on type-to-filter for every dropdown in a form.

    combobox.js leaves short lists as plain selects, so lists that are small today only change
    when they grow.
    """
    for field in form.fields.values():
        widget = field.widget
        if isinstance(widget, forms.Select) and not isinstance(widget, forms.SelectMultiple):
            widget.attrs.setdefault('data-combobox', '1')
