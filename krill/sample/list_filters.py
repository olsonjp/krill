"""Field filters for list pages ("Sample X with Passage Y").

Each list describes its filter fields once, as a FilterSpec. From that one description come:
  - the query filters (spec.apply),
  - the inputs on the page (spec.bind(request).inline / .more),
  - the removable chips, the Clear all link, and the suggestions shown when nothing matches.

Every filled-in field must match (AND). The query parameter names are part of the page address, so
people can bookmark and share a search; treat them as stable.

Matching rules:
  contains   case-insensitive; every word must appear, and "quoted words" keep their spacing
  exact      the whole value, ignoring case
  passage    exact, ignoring case; a trailing * matches the start instead (P8* finds P8, P80, P8+3)
  number     an exact aliquot number, with or without a leading #
  date_from  on or after;  date_to  on or before (aliquots with no date never match either)
  select     one of a fixed list of choices
"""
import re
from dataclasses import dataclass
from datetime import date
from typing import Callable, Optional, Tuple

from django.db.models import Q

CONTAINS = 'contains'
EXACT = 'exact'
PASSAGE = 'passage'
NUMBER = 'number'
DATE_FROM = 'date_from'
DATE_TO = 'date_to'
SELECT = 'select'

DATE_KINDS = (DATE_FROM, DATE_TO)
_WORDS = re.compile(r'"([^"]+)"|(\S+)')


def split_words(text):
    """'hela p8 "cell line"' -> ['hela', 'p8', 'cell line']"""
    return [quoted or word for quoted, word in _WORDS.findall(text or '') if (quoted or word).strip()]


def parse_date(value):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


@dataclass(frozen=True)
class FilterField:
    param: str                      # query parameter, e.g. 'f_sample'
    label: str                      # shown next to the input and in chips
    kind: str
    paths: Tuple[str, ...] = ()     # model lookups to search (OR across paths)
    placeholder: str = ''
    hint: str = ''                  # one line under the label in the More panel
    inline: bool = False            # shown in the toolbar row (otherwise in More)
    verb: str = ''                  # chip wording override, e.g. 'contain' for "Notes contain x"
    choices: Optional[Callable] = None   # SELECT: () -> [(value, label)]
    select_filter: Optional[Callable] = None  # SELECT: (queryset, value) -> queryset


@dataclass(frozen=True)
class Chip:
    text: str
    remove_url: str


class BoundField:
    """A field with its current value, ready for a template."""

    def __init__(self, field, value):
        self.field = field
        self.param = field.param
        self.label = field.label
        self.kind = field.kind
        self.value = value
        self.placeholder = field.placeholder
        self.hint = field.hint
        self.is_select = field.kind == SELECT
        self.is_date = field.kind in DATE_KINDS
        self.choices = []
        if self.is_select:
            self.choices = [(v, label, str(v) == value) for v, label in field.choices()]


class FilterBar:
    def __init__(self, inline, more, chips, clear_all_url):
        self.inline = inline
        self.more = more
        self.chips = chips
        self.clear_all_url = clear_all_url
        self.more_active = sum(1 for f in more if f.value)
        # The rules for the inline fields, repeated at the top of the More panel
        self.inline_hints = [(f.label, f.hint) for f in inline if f.hint]
        self.has_filters = bool(chips)
        self.show_clear_all = len(chips) >= 2


class FilterSpec:
    def __init__(self, fields, reset_params=()):
        self.fields = list(fields)
        # Other parameters that "Clear all" also removes (the search phrase, pills, ...)
        self.reset_params = tuple(reset_params)

    # --- reading the request --------------------------------------------------

    @staticmethod
    def value_of(query, field):
        return (query.get(field.param) or '').strip()

    def active(self, query):
        """[(field, value)] for the fields that are filled in and mean something."""
        result = []
        for field in self.fields:
            value = self.value_of(query, field)
            if not value:
                continue
            if field.kind in DATE_KINDS and parse_date(value) is None:
                continue
            if field.kind == PASSAGE and value.rstrip('*').strip() == '':
                continue
            if field.kind == SELECT and not self._select_matches(field, value):
                continue
            result.append((field, value))
        return result

    @staticmethod
    def _select_matches(field, value):
        return any(str(v) == value for v, _ in field.choices())

    # --- filtering ------------------------------------------------------------

    def apply(self, queryset, query, skip_kinds=(), only_kinds=None):
        for field, value in self.active(query):
            if field.kind in skip_kinds or (only_kinds is not None and field.kind not in only_kinds):
                continue
            queryset = self._filter(queryset, field, value)
        return queryset

    @staticmethod
    def _filter(queryset, field, value):
        kind = field.kind
        if kind == CONTAINS:
            for word in split_words(value):
                match = Q()
                for path in field.paths:
                    match |= Q(**{f'{path}__icontains': word})
                queryset = queryset.filter(match)
            return queryset
        if kind == EXACT:
            match = Q()
            for path in field.paths:
                match |= Q(**{f'{path}__iexact': value})
            return queryset.filter(match)
        if kind == PASSAGE:
            path = field.paths[0]
            if value.endswith('*'):
                return queryset.filter(**{f'{path}__istartswith': value.rstrip('*').strip()})
            return queryset.filter(**{f'{path}__iexact': value})
        if kind == NUMBER:
            number = value.lstrip('#')
            return queryset.filter(pk=int(number)) if number.isdigit() else queryset.none()
        if kind == DATE_FROM:
            return queryset.filter(**{f'{field.paths[0]}__gte': parse_date(value)})
        if kind == DATE_TO:
            return queryset.filter(**{f'{field.paths[0]}__lte': parse_date(value)})
        if kind == SELECT:
            return field.select_filter(queryset, value)
        return queryset

    # --- what the page shows --------------------------------------------------

    @staticmethod
    def chip_text(field, value):
        kind = field.kind
        if kind in DATE_KINDS:
            return f'{field.label} {value}'
        if kind == SELECT:
            label = next((label for v, label in field.choices() if str(v) == value), value)
            return f'{field.label}: {label}'
        if kind == PASSAGE:
            return f'{field.label} starts with {value.rstrip("*").strip()}' if value.endswith('*') else f'{field.label} is {value}'
        if kind in (EXACT, NUMBER):
            return f'{field.label} is {value}'
        return f'{field.label} {field.verb or "contains"} {value}'

    @staticmethod
    def url_without(request, *params):
        """The current address minus some parameters, back on page 1."""
        query = request.GET.copy()
        query.pop('page', None)
        for param in params:
            query.pop(param, None)
        encoded = query.urlencode()
        return f'?{encoded}' if encoded else request.path

    def bind(self, request, extra_chips=()):
        """Everything a template needs. extra_chips are (text, parameter) pairs for filters this spec
        does not own, such as the search phrase; they are shown first."""
        chips = [Chip(text, self.url_without(request, param)) for text, param in extra_chips]
        for field, value in self.active(request.GET):
            chips.append(Chip(self.chip_text(field, value), self.url_without(request, field.param)))
        everything = [f.param for f in self.fields] + list(self.reset_params)
        bound = [BoundField(field, self.value_of(request.GET, field)) for field in self.fields]
        return FilterBar(
            inline=[b for b in bound if b.field.inline],
            more=[b for b in bound if not b.field.inline],
            chips=chips,
            clear_all_url=self.url_without(request, *everything),
        )


# --- the lists ---------------------------------------------------------------

def _disposition_choices():
    from .models.aliquot import AliquotDisposition
    return list(AliquotDisposition.DISPOSITION_CHOICES)


def _type_choices():
    from .models.aliquot import AliquotType
    return [(str(t.pk), t.name) for t in AliquotType.objects.order_by('name')]


ALIQUOT_FILTERS = FilterSpec(
    [
        FilterField('f_sample', 'Sample', CONTAINS, ('sample__name',), inline=True,
                    placeholder='Sample', hint='Part of the sample name.'),
        FilterField('f_passage', 'Passage', PASSAGE, ('passage',), inline=True,
                    placeholder='Passage',
                    hint='Matches exactly, ignoring case: P8 finds P8 and p8, not P80. End with * to match the start, for example P8*.'),
        FilterField('f_member', 'Lab member', CONTAINS,
                    ('lab_member_initials', 'lab_member__first_name', 'lab_member__last_name', 'lab_member__username'),
                    placeholder='Name or initials', hint='Name or initials.'),
        FilterField('f_date_from', 'Date from', DATE_FROM, ('sample_date',),
                    hint='On or after. Aliquots with no sample date are left out.'),
        FilterField('f_date_to', 'Date to', DATE_TO, ('sample_date',),
                    hint='On or before. Aliquots with no sample date are left out.'),
        FilterField('f_location', 'Location', CONTAINS,
                    ('location__box__name', 'location__box__rack__shelf__device__name'),
                    placeholder='Freezer or box', hint='Part of a freezer or box name.'),
        FilterField('f_number', 'Aliquot number', NUMBER, ('pk',),
                    placeholder='e.g. 1234', hint='The exact aliquot number.'),
        FilterField('disposition', 'Disposition', SELECT, choices=_disposition_choices,
                    select_filter=lambda qs, value: qs.filter(disposition__disposition_type=value)),
        FilterField('aliquot_type', 'Type', SELECT, choices=_type_choices,
                    select_filter=lambda qs, value: qs.filter(aliquot_type_id=int(value))),
    ],
    reset_params=('q', 'sample', 'checked_out_by', 'hide_finished', 'low_count'),
)

SAMPLE_FILTERS = FilterSpec(
    [
        FilterField('f_source', 'Source', CONTAINS, ('source__name',), inline=True,
                    placeholder='Source', hint='Part of the source name.'),
        FilterField('f_experiment', 'Experiment', CONTAINS, ('experiment',), inline=True,
                    placeholder='Experiment', hint='Part of the experiment text.'),
        FilterField('f_notes', 'Notes', CONTAINS, ('notes',), inline=True, verb='contain',
                    placeholder='Notes', hint='Part of the notes.'),
    ],
    reset_params=('q', 'checked_out_by', 'hide_finished', 'low_count'),
)
