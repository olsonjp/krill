"""Low-count alerts: warn when a sample has few stored aliquots left.

A sample's count is its aliquots whose disposition is Stored (no box position needed; soft-deleted
aliquots are ignored). It is **alert** at or below the alert level and **warn** at or below the warn
level. The levels come from the lab default (SiteConfiguration, set in Settings) unless the sample
has its own. A sample with no aliquots at all is not checked, and a sample can opt out with
Sample.low_count_check.
"""
from typing import Optional

from person.models import SiteConfiguration

ALERT = 'alert'
WARN = 'warn'


def levels_for(sample, config=None):
    """(warn, alert) for a sample. The alert level is never above the warn level."""
    config = config or SiteConfiguration.load()
    warn = config.low_count_warn if sample.low_count_warn is None else sample.low_count_warn
    alert = config.low_count_alert if sample.low_count_alert is None else sample.low_count_alert
    return warn, min(alert, warn)


def state_for_count(count, warn, alert) -> Optional[str]:
    if count <= alert:
        return ALERT
    if count <= warn:
        return WARN
    return None


def state_for(sample, config=None) -> Optional[str]:
    """'alert', 'warn' or None for a sample annotated by Sample.objects.with_stored_count().

    Ignores the opt-out switch, so a silenced sample still shows how low it is.
    """
    if not sample.aliquot_total:
        return None
    warn, alert = levels_for(sample, config)
    return state_for_count(sample.stored_count, warn, alert)


def low_samples():
    """Every sample that is at or below its warn level, as dicts with its counts and levels.

    Samples that opted out are included with silenced=True; callers decide what to do with them.
    """
    from .models.sample import Sample

    config = SiteConfiguration.load()
    rows = []
    for sample in Sample.objects.with_stored_count().filter(aliquot_total__gt=0).order_by('name', 'id'):
        warn, alert = levels_for(sample, config)
        state = state_for_count(sample.stored_count, warn, alert)
        if state:
            rows.append({
                'sample': sample,
                'count': sample.stored_count,
                'warn': warn,
                'alert': alert,
                'state': state,
                'silenced': not sample.low_count_check,
            })
    return rows
