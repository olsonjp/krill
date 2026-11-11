"""What needs attention: one place that works out the lab's pending action items.

The header pill, the overview page and (later) email notifications all read from here, so they
always agree. To add a source, write a function that returns a list of AttentionItem and
register it with register_source(). Each item has a stable `key`, so silencing and email
de-duplication can refer to the same item over time.

An item is silenced by a flag on the record it is about (Consumable.alerts_silenced, or a sample's
low_count_check being off), not by a separate table, because the lab sets such things per record.
Silenced items are still returned, marked silenced, so the overview can show them; they are left
out of the counts.
"""
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Callable, List, Optional

from django.db.models import F
from django.urls import reverse

LEVEL_ALERT = 'alert'
LEVEL_WARN = 'warn'
_LEVEL_RANK = {LEVEL_WARN: 1, LEVEL_ALERT: 2}

EXPIRING_SOON_DAYS = 30


@dataclass(frozen=True)
class AttentionItem:
    source: str        # source name, e.g. 'low_stock'
    key: str           # stable id, e.g. 'low_stock:consumable:12'
    title: str
    detail: str
    level: str         # LEVEL_ALERT or LEVEL_WARN
    url: str           # where to go to deal with it
    silenced: bool
    target_type: str   # what the item is about: 'consumable'
    target_id: int


@dataclass(frozen=True)
class Source:
    name: str
    label: str
    icon: str
    collect: Callable[[], List[AttentionItem]]
    available: Callable[[], bool]


SOURCES: List[Source] = []
# target_type -> function(target_id, silenced) -> True if a record was changed
SILENCERS = {}


def register_source(name, label, icon, collect, available=lambda: True):
    SOURCES.append(Source(name, label, icon, collect, available))


def register_silencer(target_type, setter):
    SILENCERS[target_type] = setter


def _number(value):
    """Decimal('3.000') -> '3'"""
    return format(value.normalize(), 'f')


# --- consumables -------------------------------------------------------------

def _consumables_enabled():
    from person.models import SiteConfiguration
    return SiteConfiguration.load().consumables_enabled


def _consumable_url(consumable):
    return reverse('consumables:detail', kwargs={'type': 'consumable', 'pk': consumable.pk})


def low_stock_items():
    from consumables.models.consumable import Consumable
    rows = Consumable.objects.active().filter(
        low_stock_threshold__isnull=False,
        quantity__lte=F('low_stock_threshold'),
    ).order_by('name', 'id')
    return [
        AttentionItem(
            source='low_stock',
            key=f'low_stock:consumable:{c.pk}',
            title=c.name,
            detail=(
                f'Out of stock (reorder at {_number(c.low_stock_threshold)} {c.unit})'
                if c.quantity <= 0 else
                f'{_number(c.quantity)} {c.unit} left (reorder at {_number(c.low_stock_threshold)})'
            ),
            level=LEVEL_ALERT if c.quantity <= 0 else LEVEL_WARN,
            url=_consumable_url(c),
            silenced=c.alerts_silenced,
            target_type='consumable',
            target_id=c.pk,
        )
        for c in rows
    ]


def expiring_items():
    from consumables.models.consumable import Consumable
    today = date.today()
    rows = Consumable.objects.active().filter(
        expiration_date__isnull=False,
        expiration_date__gte=today,
        expiration_date__lte=today + timedelta(days=EXPIRING_SOON_DAYS),
    ).order_by('expiration_date', 'name', 'id')
    items = []
    for c in rows:
        days = (c.expiration_date - today).days
        when = 'today' if days == 0 else f'in {days} day{"s" if days != 1 else ""}'
        items.append(AttentionItem(
            source='expiring',
            key=f'expiring:consumable:{c.pk}',
            title=c.name,
            detail=f'Expires {c.expiration_date:%Y-%m-%d} ({when})',
            level=LEVEL_WARN,
            url=_consumable_url(c),
            silenced=c.alerts_silenced,
            target_type='consumable',
            target_id=c.pk,
        ))
    return items


# --- low sample counts -------------------------------------------------------

def low_count_items():
    from sample import low_count
    items = []
    for row in low_count.low_samples():
        sample, count = row['sample'], row['count']
        left = 'No stored aliquots left' if count == 0 else f'{count} stored aliquot{"s" if count != 1 else ""} left'
        items.append(AttentionItem(
            source='low_count',
            key=f'low_count:sample:{sample.pk}',
            title=sample.name,
            detail=f'{left} (alert at {row["alert"]} or fewer, warn at {row["warn"]} or fewer)',
            level=LEVEL_ALERT if row['state'] == low_count.ALERT else LEVEL_WARN,
            url=reverse('sample:detail', kwargs={'type': 'sample', 'pk': sample.pk}),
            silenced=row['silenced'],
            target_type='sample',
            target_id=sample.pk,
        ))
    return items


def _silence_sample(target_id, silenced):
    from sample.models.sample import Sample
    # Silenced means the low-count check is switched off for this sample
    return bool(Sample.objects.filter(pk=target_id).update(low_count_check=not silenced))


def _silence_consumable(target_id, silenced):
    from consumables.models.consumable import Consumable
    return bool(Consumable.objects.filter(pk=target_id, deleted=False).update(alerts_silenced=silenced))


register_source('low_stock', 'Low stock', 'production_quantity_limits', low_stock_items, _consumables_enabled)
register_source('expiring', 'Expiring soon', 'event_busy', expiring_items, _consumables_enabled)
register_silencer('consumable', _silence_consumable)
register_source('low_count', 'Low sample counts', 'science', low_count_items)
register_silencer('sample', _silence_sample)


# --- reading it --------------------------------------------------------------

def groups():
    """[{'source': Source, 'active': [...], 'silenced': [...]}] for every source that is available."""
    result = []
    for source in SOURCES:
        if not source.available():
            continue
        items = source.collect()
        result.append({
            'source': source,
            'active': [i for i in items if not i.silenced],
            'silenced': [i for i in items if i.silenced],
        })
    return result


def worst_level(items) -> Optional[str]:
    levels = [i.level for i in items]
    return max(levels, key=lambda lv: _LEVEL_RANK[lv]) if levels else None


def summary():
    """{'count': int, 'level': 'alert' | 'warn' | None} over the items that are not silenced."""
    active = [i for g in groups() for i in g['active']]
    return {'count': len(active), 'level': worst_level(active)}


def silence(target_type, target_id, silenced=True):
    """Silence or unsilence everything about one record. Returns False if nothing matched."""
    setter = SILENCERS.get(target_type)
    return bool(setter and setter(target_id, silenced))
