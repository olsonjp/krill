import json
import csv
import io
import logging
from datetime import datetime, timedelta

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum, Avg
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.views.generic import ListView, DetailView
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from .models import ReportTemplate, Report, ScheduledReport, Alert
from sample.models import Sample, Aliquot
from sample.models.aliquot import AliquotLocation
from storage.models.storage import Device, Box
from person.models import UserAuditLog

logger = logging.getLogger(__name__)


# Main Reports Dashboard
@login_required
def reports_dashboard(request):
    """Main reports dashboard view"""
    try:
        # Get basic statistics
        total_reports = Report.objects.count()
        pending_reports = Report.objects.filter(status='pending').count()
        active_alerts = Alert.objects.filter(status='active').count()
        open_issues = 0  # Issue tracking removed

        # Get recent reports
        recent_reports = Report.objects.filter(created_by=request.user).order_by('-created_at')[:5]

        # Get recent alerts
        recent_alerts = Alert.objects.filter(status='active').order_by('-created_at')[:5]

        # Get recent issues (removed - issue tracking disabled)
        recent_issues = []

        context = {
            'total_reports': total_reports,
            'pending_reports': pending_reports,
            'active_alerts': active_alerts,
            'open_issues': open_issues,
            'recent_reports': recent_reports,
            'recent_alerts': recent_alerts,
            'recent_issues': recent_issues,
        }

        return render(request, 'reports/reports_dashboard.html', context)
    except Exception as e:
        # Fallback to basic template if there are any errors
        return render(request, 'reports/reports_dashboard.html', {
            'total_reports': 0,
            'pending_reports': 0,
            'active_alerts': 0,
            'open_issues': 0,
            'recent_reports': [],
            'recent_alerts': [],
            'recent_issues': [],
        })


# Dashboard Statistics API
@login_required
def dashboard_stats(request):
    """Enhanced dashboard statistics API with resilient error handling"""
    stats = {}
    errors = []

    # Active samples count
    try:
        active_samples = Sample.objects.count()
        stats['active_samples'] = active_samples
    except Exception as e:
        logger.error(f"Error fetching active samples count: {str(e)}", exc_info=True)
        errors.append(f"active_samples: {str(e)}")
        stats['active_samples'] = 0

    # Storage usage calculation
    try:
        total_slots = 0
        used_slots = 0
        # Only fetch the fields we need for calculation
        boxes = Box.objects.only('rows', 'columns')
        for box in boxes:
            total_slots += box.rows * box.columns
        used_slots = AliquotLocation.objects.count()
        storage_usage = 0
        if total_slots > 0:
            storage_usage = round((used_slots / total_slots) * 100)
        stats['total_slots'] = total_slots
        stats['used_slots'] = used_slots
        stats['storage_usage'] = storage_usage
    except Exception as e:
        logger.error(f"Error calculating storage usage: {str(e)}", exc_info=True)
        errors.append(f"storage_usage: {str(e)}")
        stats['total_slots'] = 0
        stats['used_slots'] = 0
        stats['storage_usage'] = 0

    # Recent reports count
    try:
        recent_reports = Report.objects.filter(
            created_at__gte=timezone.now() - timedelta(days=7)
        ).count()
        stats['recent_reports'] = recent_reports
    except Exception as e:
        logger.error(f"Error fetching recent reports count: {str(e)}", exc_info=True)
        errors.append(f"recent_reports: {str(e)}")
        stats['recent_reports'] = 0

    # Active alerts count
    try:
        active_alerts = Alert.objects.filter(status='active').count()
        stats['alerts'] = active_alerts
    except Exception as e:
        logger.error(f"Error fetching active alerts count: {str(e)}", exc_info=True)
        errors.append(f"alerts: {str(e)}")
        stats['alerts'] = 0

    # Recent activity count
    try:
        recent_activity = UserAuditLog.objects.filter(
            timestamp__gte=timezone.now() - timedelta(days=1)
        ).count()
        stats['recent_activity'] = recent_activity
    except Exception as e:
        logger.error(f"Error fetching recent activity count: {str(e)}", exc_info=True)
        errors.append(f"recent_activity: {str(e)}")
        stats['recent_activity'] = 0

    # Storage device status (Device has no is_active; all devices counted as active)
    try:
        storage_devices = Device.objects.count()
        active_devices = storage_devices
        stats['storage_devices'] = storage_devices
        stats['active_devices'] = active_devices
    except Exception as e:
        logger.error(f"Error fetching storage device status: {str(e)}", exc_info=True)
        errors.append(f"storage_devices: {str(e)}")
        stats['storage_devices'] = 0
        stats['active_devices'] = 0

    # Sample statistics
    try:
        total_aliquots = Aliquot.objects.count()
        stored_aliquots = AliquotLocation.objects.count()
        stats['total_aliquots'] = total_aliquots
        stats['stored_aliquots'] = stored_aliquots
    except Exception as e:
        logger.error(f"Error fetching aliquot statistics: {str(e)}", exc_info=True)
        errors.append(f"aliquot_stats: {str(e)}")
        stats['total_aliquots'] = 0
        stats['stored_aliquots'] = 0

    # Include errors in response if any occurred (for debugging)
    if errors:
        stats['_errors'] = errors
        logger.warning(f"Dashboard stats completed with {len(errors)} errors: {', '.join(errors)}")

    return JsonResponse(stats)


# Report Generation API
@login_required
@require_http_methods(["POST"])
def generate_report(request):
    """Generate a new report"""
    try:
        data = json.loads(request.body)
        template_id = data.get('template_id')
        report_name = data.get('name', 'Generated Report')
        report_format = data.get('format', 'pdf')
        parameters = data.get('parameters', {})

        template = get_object_or_404(ReportTemplate, id=template_id, is_active=True)

        # Create report instance
        report = Report.objects.create(
            template=template,
            name=report_name,
            format=report_format,
            parameters=parameters,
            created_by=request.user
        )

        # Generate report data based on type
        sample_data = generate_sample_report_data(template.report_type, parameters)
        report.mark_complete(result_data=sample_data)

        return JsonResponse({
            'success': True,
            'report_id': report.id,
            'status': report.status,
            'message': 'Report generated successfully'
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def generate_audit_report(request):
    """Generate a storage audit report with random slot selection"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            sample_size = int(data.get('sample_size', 10))
            include_empty_checks = data.get('include_empty_checks', False)
            report_name = data.get('name', f'Storage Audit - {timezone.now().strftime("%Y-%m-%d")}')

            # Create or get the storage audit template
            template, created = ReportTemplate.objects.get_or_create(
                report_type='storage_audit',
                defaults={
                    'name': 'Storage Audit Template',
                    'description': 'Random audit of occupied storage slots',
                    'template_data': {'default_sample_size': 10},
                    'created_by': request.user
                }
            )

            # Create report instance
            parameters = {
                'sample_size': sample_size,
                'include_empty_checks': include_empty_checks
            }

            report = Report.objects.create(
                template=template,
                name=report_name,
                format='json',  # Audit reports work best as JSON for data processing
                parameters=parameters,
                created_by=request.user
            )

            # Generate audit data
            audit_data = generate_storage_audit_data(parameters)
            report.mark_complete(result_data=audit_data)

            return JsonResponse({
                'success': True,
                'report_id': report.id,
                'status': report.status,
                'message': 'Audit report generated successfully',
                'data': audit_data
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    # GET request - show audit report form
    return render(request, 'reports/audit_report_form.html')


@login_required
def report_list(request):
    """List all reports for the current user"""
    reports = Report.objects.filter(created_by=request.user).order_by('-created_at')

    # Pagination
    paginator = Paginator(reports, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'reports': page_obj,
        'total_reports': reports.count(),
        'pending_reports': reports.filter(status='pending').count(),
        'completed_reports': reports.filter(status='complete').count(),
    }
    return render(request, 'reports/report_list.html', context)


@login_required
def report_detail(request, report_id):
    """View report details"""
    report = get_object_or_404(Report, id=report_id, created_by=request.user)
    context = {'report': report}
    return render(request, 'reports/report_detail.html', context)


@login_required
def download_report(request, report_id):
    """Download generated report file"""
    report = get_object_or_404(Report, id=report_id, created_by=request.user)

    if report.status != 'complete':
        return JsonResponse({'error': 'Report not ready for download'}, status=400)

    if report.format == 'csv':
        return generate_csv_response(report.result_data)
    elif report.format == 'json':
        return JsonResponse(report.result_data)
    else:
        # For PDF and Excel, return file path info
        return JsonResponse({
            'file_path': report.file_path,
            'file_size': report.file_size
        })


# Alert System API
@login_required
def alert_list(request):
    """List all alerts"""
    alerts = Alert.objects.all().order_by('-created_at')

    # Filter by status if provided
    status_filter = request.GET.get('status')
    if status_filter:
        alerts = alerts.filter(status=status_filter)

    # Pagination
    paginator = Paginator(alerts, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'alerts': page_obj,
        'total_alerts': alerts.count(),
        'active_alerts': alerts.filter(status='active').count(),
        'critical_alerts': alerts.filter(severity='critical', status='active').count(),
    }
    return render(request, 'reports/alert_list.html', context)


@login_required
@require_http_methods(["POST"])
def acknowledge_alert(request, alert_id):
    """Acknowledge an alert"""
    try:
        alert = get_object_or_404(Alert, id=alert_id)
        alert.acknowledge(request.user)
        return JsonResponse({'success': True, 'message': 'Alert acknowledged'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def resolve_alert(request, alert_id):
    """Resolve an alert"""
    try:
        alert = get_object_or_404(Alert, id=alert_id)
        alert.resolve(request.user)
        return JsonResponse({'success': True, 'message': 'Alert resolved'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def create_alert(request):
    """Create a new alert"""
    try:
        data = json.loads(request.body)
        alert = Alert.objects.create(
            title=data['title'],
            message=data['message'],
            severity=data.get('severity', 'medium'),
            alert_type=data.get('alert_type', 'general'),
            target_type=data.get('target_type', ''),
            target_id=data.get('target_id'),
        )
        return JsonResponse({
            'success': True,
            'alert_id': alert.id,
            'message': 'Alert created successfully'
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# Storage Management Dashboard API
@login_required
def storage_dashboard(request):
    """Storage overview statistics"""
    try:
        # Device statistics
        total_devices = Device.objects.count()
        # Since Device model doesn't have is_active field, all devices are considered active
        active_devices = total_devices

        # Box statistics
        total_boxes = Box.objects.count()
        used_boxes = Box.objects.filter(aliquotlocation__isnull=False).distinct().count()
        available_boxes = total_boxes - used_boxes

        # Capacity statistics
        total_slots = 0
        used_slots = 0
        boxes = Box.objects.all()
        for box in boxes:
            total_slots += box.rows * box.columns
        used_slots = AliquotLocation.objects.count()

        # Freezer status - calculate per device
        freezer_status = []
        for device in Device.objects.all()[:4]:
            # Calculate device-specific capacity
            device_boxes = Box.objects.filter(rack__shelf__device=device)
            device_total_slots = sum(box.rows * box.columns for box in device_boxes)
            device_used_slots = AliquotLocation.objects.filter(box__rack__shelf__device=device).count()
            device_usage_percent = round((device_used_slots / device_total_slots * 100) if device_total_slots > 0 else 0)
            
            freezer_status.append({
                'name': device.name,
                'status': 'operational',
                'capacity': f"{device_used_slots}/{device_total_slots}",
                'usage_percent': device_usage_percent
            })

        stats = {
            'total_devices': total_devices,
            'active_devices': active_devices,
            'total_boxes': total_boxes,
            'used_boxes': used_boxes,
            'available_boxes': available_boxes,
            'total_slots': total_slots,
            'used_slots': used_slots,
            'stored_aliquots': used_slots,  # Alias for JavaScript compatibility
            'freezer_status': freezer_status,
        }
        return JsonResponse(stats)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# Helper functions
def generate_sample_report_data(report_type, parameters):
    """Generate sample data for reports"""
    if report_type == 'sample_inventory':
        return {
            'total_samples': Sample.objects.count(),
            'samples_by_experiment': list(Sample.objects.values('experiment').annotate(count=Count('id'))),
        }
    elif report_type == 'storage_capacity':
        total_slots = sum(box.rows * box.columns for box in Box.objects.all())
        used_slots = AliquotLocation.objects.count()
        return {
            'total_slots': total_slots,
            'used_slots': used_slots,
            'available_slots': total_slots - used_slots,
            'usage_percentage': round((used_slots / total_slots * 100) if total_slots > 0 else 0),
        }
    elif report_type == 'storage_audit':
        return generate_storage_audit_data(parameters)
    else:
        return {'message': 'Report data placeholder'}


def generate_storage_audit_data(parameters):
    """Generate storage audit data with random slot selection"""
    import random
    from django.db.models import Prefetch

    # Get parameters with defaults
    sample_size = int(parameters.get('sample_size', 10))
    include_empty_checks = parameters.get('include_empty_checks', False)

    # Get all occupied slots
    occupied_locations = AliquotLocation.objects.select_related(
        'aliquot__sample',
        'box__device__site'
    ).prefetch_related(
        Prefetch('aliquot__sample__aliquots', queryset=Aliquot.objects.all())
    ).all()

    total_occupied = occupied_locations.count()

    if total_occupied == 0:
        return {
            'total_occupied_slots': 0,
            'sample_size': sample_size,
            'audit_slots': [],
            'summary': 'No occupied slots found for audit'
        }

    # Randomly select slots for audit
    actual_sample_size = min(sample_size, total_occupied)
    audit_slots = random.sample(list(occupied_locations), actual_sample_size)

    # Format audit data
    audit_data = []
    for location in audit_slots:
        slot_data = {
            'location_id': location.id,
            'site': location.box.device.site.name if location.box.device.site else 'Unknown',
            'device': location.box.device.name,
            'box': location.box.name,
            'row': location.row,
            'column': location.column,
            'aliquot_id': location.aliquot.id if location.aliquot else None,
            'sample_name': location.aliquot.sample.name if location.aliquot and location.aliquot.sample else 'Unknown',
            'sample_id': location.aliquot.sample.id if location.aliquot and location.aliquot.sample else None,
            'aliquot_quantity': location.aliquot.quantity if location.aliquot else 0,
            'expected_tubes': location.aliquot.quantity if location.aliquot else 0,
            'actual_tubes': 0,  # This would be filled in during physical audit
            'discrepancy': False,  # This would be calculated during physical audit
            'notes': '',  # For audit notes
        }
        audit_data.append(slot_data)

    # If including empty slot checks, also randomly select some empty slots
    empty_audit_data = []
    if include_empty_checks:
        # Get all boxes and their total capacity
        all_boxes = Box.objects.select_related('device__site').all()
        empty_slots = []

        for box in all_boxes:
            occupied_in_box = AliquotLocation.objects.filter(box=box).values_list('row', 'column')
            occupied_set = set(occupied_in_box)

            for row in range(1, box.rows + 1):
                for col in range(1, box.columns + 1):
                    if (row, col) not in occupied_set:
                        empty_slots.append({
                            'site': box.device.site.name if box.device.site else 'Unknown',
                            'device': box.device.name,
                            'box': box.name,
                            'row': row,
                            'column': col,
                            'expected_empty': True,
                            'actual_empty': True,  # This would be filled in during physical audit
                            'notes': ''
                        })

        # Randomly select some empty slots for verification
        if empty_slots:
            empty_sample_size = min(5, len(empty_slots))  # Check up to 5 empty slots
            empty_audit_data = random.sample(empty_slots, empty_sample_size)

    return {
        'total_occupied_slots': total_occupied,
        'sample_size': actual_sample_size,
        'audit_slots': audit_data,
        'empty_slots_checked': include_empty_checks,
        'empty_audit_slots': empty_audit_data,
        'generated_at': timezone.now().isoformat(),
        'summary': f'Random audit of {actual_sample_size} occupied slots from {total_occupied} total occupied slots'
    }


def generate_csv_response(data):
    """Generate CSV response from data"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="report.csv"'

    writer = csv.writer(response)

    # Write headers and data based on data structure
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, list) and value:
                # Write list data
                writer.writerow([key])
                if isinstance(value[0], dict):
                    writer.writerow(value[0].keys())
                    for row in value:
                        writer.writerow(row.values())
                else:
                    for row in value:
                        writer.writerow([row])
                writer.writerow([])  # Empty row for separation
            else:
                writer.writerow([key, value])

    return response


# Class-based views for templates
class ReportListView(LoginRequiredMixin, ListView):
    model = Report
    template_name = 'reports/report_list.html'
    context_object_name = 'reports'
    paginate_by = 20

    def get_queryset(self):
        return Report.objects.filter(created_by=self.request.user).order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_reports'] = Report.objects.filter(created_by=self.request.user).count()
        context['pending_reports'] = Report.objects.filter(created_by=self.request.user, status='pending').count()
        context['completed_reports'] = Report.objects.filter(created_by=self.request.user, status='complete').count()
        return context


class AlertListView(LoginRequiredMixin, ListView):
    model = Alert
    template_name = 'reports/alert_list.html'
    context_object_name = 'alerts'
    paginate_by = 20

    def get_queryset(self):
        queryset = Alert.objects.all().order_by('-created_at')
        status_filter = self.request.GET.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_alerts'] = Alert.objects.count()
        context['active_alerts'] = Alert.objects.filter(status='active').count()
        context['critical_alerts'] = Alert.objects.filter(severity='critical', status='active').count()
        return context
