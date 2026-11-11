from datetime import date, timedelta

from django.shortcuts import redirect, render
from django.views.generic import View
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.http import JsonResponse
from django.utils import timezone

from sample.models.sample import Sample
from sample.models.aliquot import Aliquot, AliquotLocation
from storage.models.storage import Box
from person.models import UserAuditLog, UserPreference, SiteConfiguration, UserRole
from person.decorators import require_minimum_role

__all__ = (
    'HomeView',
    'ReportsView',
    'SettingsView',
    'dashboard_stats',
)

@method_decorator(login_required, name='dispatch')
class HomeView(View):
    template_name = 'krill/home.html'

    def get(self, request):
        # Get dashboard statistics
        stats = get_dashboard_statistics()
        freezers = get_freezer_cards()
        return render(request, self.template_name, {
            'stats': stats,
            'freezers': freezers,
            'show_sites': len({card['device'].site_id for card in freezers}) > 1,
            'checked_out': get_checked_out(request.user),
            'lab_checkouts': get_lab_checkouts(request.user),
            'audits_in_progress': get_audits_in_progress(),
            'recent_activity': get_recent_activity(),
        })

@login_required
def dashboard_stats(request):
    """API endpoint for dashboard statistics"""
    stats = get_dashboard_statistics()
    return JsonResponse(stats)

def get_dashboard_statistics():
    """Calculate dashboard statistics from database"""
    try:
        # Active samples (non-deleted)
        active_samples = Sample.objects.count()
        # Storage usage calculation
        total_slots = 0
        used_slots = 0
        # Calculate total slots from all boxes
        boxes = Box.objects.all()
        for box in boxes:
            total_slots += box.rows * box.columns
        # Calculate used slots from aliquot locations
        used_slots = AliquotLocation.objects.count()
        # Calculate percentage
        storage_usage = 0
        if total_slots > 0:
            storage_usage = round((used_slots / total_slots) * 100)
        # Recent reports (using audit logs for now)
        # In a real system, you'd have a Report model
        recent_reports = UserAuditLog.objects.filter(
            action='report_generated',
            timestamp__gte=timezone.now() - timedelta(days=7)
        ).count()
        # Alerts (using audit logs for now)
        # In a real system, you'd have an Alert model
        alerts = UserAuditLog.objects.filter(
            action__in=['alert_created', 'warning_created'],
            timestamp__gte=timezone.now() - timedelta(days=1)
        ).count()
        # Consumables stats (only when feature is enabled)
        low_stock_count = 0
        expiring_soon_count = 0
        site_config = SiteConfiguration.load()
        if site_config.consumables_enabled:
            from consumables.models.consumable import Consumable
            low_stock_count = Consumable.objects.low_stock().count()
            expiring_soon_count = Consumable.objects.active().filter(
                expiration_date__isnull=False,
                expiration_date__lte=date.today() + timedelta(days=30),
                expiration_date__gte=date.today(),
            ).count()

        return {
            'active_samples': active_samples,
            'storage_usage': storage_usage,
            'recent_reports': recent_reports,
            'alerts': alerts,
            'total_slots': total_slots,
            'used_slots': used_slots,
            'aliquots': Aliquot.objects.filter(deleted=False).count(),
            'low_stock_count': low_stock_count,
            'expiring_soon_count': expiring_soon_count,
        }
    except Exception as e:
        # Return default values if there's an error
        return {
            'active_samples': 0,
            'storage_usage': 0,
            'recent_reports': 0,
            'alerts': 0,
            'total_slots': 0,
            'used_slots': 0,
            'aliquots': 0,
            'low_stock_count': 0,
            'expiring_soon_count': 0,
        }

def time_ago(moment):
    """'3 hours ago' style text for a past datetime."""
    if moment is None:
        return 'No activity yet'
    diff = timezone.now() - moment
    if diff.days > 0:
        return f"{diff.days} day{'s' if diff.days != 1 else ''} ago"
    if diff.seconds >= 3600:
        hours = diff.seconds // 3600
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    if diff.seconds >= 60:
        minutes = diff.seconds // 60
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    return 'Just now'


FILL_WARN = 70    # amber above this percentage
FILL_FULL = 90    # red above this percentage


def fill_level(percent):
    if percent > FILL_FULL:
        return 'full'
    if percent > FILL_WARN:
        return 'warn'
    return 'ok'


def get_freezer_cards():
    """One card per freezer or dewar: how full it is, and when something last changed in it."""
    from django.db.models import Count, F, Max, Sum
    from storage.models.storage import Device

    capacity = {
        row['rack__shelf__device']: row['slots']
        for row in Box.objects.values('rack__shelf__device').annotate(slots=Sum(F('rows') * F('columns')))
    }
    usage = {
        row['box__rack__shelf__device']: row
        for row in AliquotLocation.objects.values('box__rack__shelf__device').annotate(used=Count('id'), last=Max('updated_at'))
    }
    cards = []
    for device in Device.objects.select_related('site').order_by('name'):
        total = capacity.get(device.pk) or 0
        used = usage.get(device.pk, {}).get('used', 0)
        percent = round(used * 100 / total) if total else 0
        cards.append({
            'device': device,
            'used': used,
            'total': total,
            'percent': percent,
            'level': fill_level(percent),
            'last_activity': time_ago(usage.get(device.pk, {}).get('last')) if used else 'Empty',
        })
    return cards


def get_checked_out(user, limit=5):
    """The signed-in user's In Use aliquots, newest checkout first, with how many children each has."""
    from django.db.models import Count

    mine = Aliquot.objects.filter(checked_out_by=user, disposition__disposition_type='in_use')
    rows = (
        mine.select_related('sample', 'aliquot_type')
        .annotate(child_count=Count('children'))
        .order_by('-checked_out_at', '-id')[:limit]
    )
    return {
        'total': mine.count(),
        'items': [
            {'aliquot': a, 'out': time_ago(a.checked_out_at), 'children': a.child_count}
            for a in rows
        ],
    }


def get_lab_checkouts(user):
    """Everyone's checked-out aliquots and how many people have them. Only for lab managers and admins."""
    if UserRole.get_or_create_for_user(user).role not in ('lab_manager', 'lab_admin'):
        return None
    out = Aliquot.objects.filter(checked_out_by__isnull=False, disposition__disposition_type='in_use')
    return {
        'aliquots': out.count(),
        'people': out.values('checked_out_by').distinct().count(),
    }


def get_audits_in_progress(limit=3):
    """Storage audits that still have slots to check, most recent first."""
    from reports.models import Report
    from reports.views import audit_progress

    audits = []
    for report in Report.objects.filter(template__report_type='storage_audit', status='complete').select_related('created_by'):
        progress = audit_progress(report.result_data)
        if progress['total'] and not progress['complete']:
            audits.append({'report': report, 'progress': progress})
            if len(audits) == limit:
                break
    return audits


ACTIVITY_VERBS = {
    'sample_created': 'created sample', 'sample_updated': 'updated sample', 'sample_deleted': 'archived sample',
    'aliquot_created': 'created aliquot', 'aliquot_updated': 'updated aliquot',
}


def activity_link(activity):
    """Where an activity entry should lead."""
    from django.urls import reverse
    kind = (activity.target_type or '').lower()
    if activity.target_id:
        if 'sample' in activity.action or kind == 'sample':
            return reverse('sample:detail', kwargs={'type': 'sample', 'pk': activity.target_id})
        if 'aliquot' in activity.action or kind == 'aliquot':
            return reverse('sample:detail', kwargs={'type': 'aliquot', 'pk': activity.target_id})
        if kind == 'user':
            return reverse('person:user_detail', args=[activity.target_id])
    if 'aliquot' in activity.action:
        return reverse('sample:sample_list') + '?type=aliquot'
    return reverse('sample:sample_list')


def get_recent_activity(limit=8):
    """Recent activity written as a sentence: who did what to which item, and where it is stored."""
    try:
        logs = list(UserAuditLog.objects.select_related('user').order_by('-timestamp')[:limit])
        aliquot_ids = [log.target_id for log in logs if log.target_id and (log.target_type or '').lower() == 'aliquot']
        places = {
            loc.aliquot_id: f"{loc.box.rack.shelf.device.name} / Box {loc.box.name}"
            for loc in AliquotLocation.objects.filter(aliquot_id__in=aliquot_ids)
            .select_related('box__rack__shelf__device')
        }
        activities = []
        for log in logs:
            verb = ACTIVITY_VERBS.get(log.action, log.action.replace('_', ' '))
            activities.append({
                'user': log.user.username if log.user else 'System',
                'verb': verb,
                'target': log.target_name or '',
                'place': places.get(log.target_id, ''),
                'time_ago': time_ago(log.timestamp),
                'action_type': log.action,
                'url': activity_link(log),
            })
        return activities
    except Exception:
        return []

@method_decorator(login_required, name='dispatch')
class ReportsView(View):
    template_name = 'krill/reports.html'

    def get(self, request):
        return render(request, self.template_name)
@method_decorator(login_required, name='dispatch')
class SettingsView(View):
    template_name = 'krill/settings.html'

    def get(self, request):
        user_preference, _ = UserPreference.objects.get_or_create(
            user=request.user,
            defaults={'dark_mode': False}
        )
        return render(request, self.template_name, {
            'user_preference': user_preference,
            'site_config': SiteConfiguration.load(),
        })

    def post(self, request):
        from person.models import UserRole
        user_role = UserRole.get_or_create_for_user(request.user)
        if user_role.role != 'lab_admin':
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("Only lab admins can change site configuration.")

        config = SiteConfiguration.load()
        consumables_enabled = request.POST.get('consumables_enabled') == 'on'
        consumables_ordering_enabled = (
            request.POST.get('consumables_ordering_enabled') == 'on'
            and consumables_enabled
        )
        config.consumables_enabled = consumables_enabled
        config.consumables_ordering_enabled = consumables_ordering_enabled
        config.updated_by = request.user
        config.save()

        UserAuditLog.log_action(
            user=request.user,
            action='update',
            target_type='SiteConfiguration',
            target_id=config.pk,
            target_name='Site Configuration',
            details={
                'consumables_enabled': consumables_enabled,
                'consumables_ordering_enabled': consumables_ordering_enabled,
            },
            request=request,
        )

        from django.contrib import messages
        messages.success(request, 'Site configuration saved.')
        return redirect('settings')
