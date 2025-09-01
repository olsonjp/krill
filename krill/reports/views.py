import json
import csv
import io
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
    """Enhanced dashboard statistics API"""
    try:
        # Active samples count
        active_samples = Sample.objects.count()
        
        # Storage usage calculation
        total_slots = 0
        used_slots = 0
        boxes = Box.objects.all()
        for box in boxes:
            total_slots += box.rows * box.columns
        used_slots = AliquotLocation.objects.count()
        storage_usage = 0
        if total_slots > 0:
            storage_usage = round((used_slots / total_slots) * 100)
        
        # Recent reports count
        recent_reports = Report.objects.filter(
            created_at__gte=timezone.now() - timedelta(days=7)
        ).count()
        
        # Active alerts count
        active_alerts = Alert.objects.filter(status='active').count()
        
        # Recent activity count
        recent_activity = UserAuditLog.objects.filter(
            timestamp__gte=timezone.now() - timedelta(days=1)
        ).count()
        
        # Storage device status
        storage_devices = Device.objects.count()
        active_devices = Device.objects.filter(is_active=True).count()
        
        # Sample statistics
        total_aliquots = Aliquot.objects.count()
        stored_aliquots = AliquotLocation.objects.count()
        
        stats = {
            'active_samples': active_samples,
            'storage_usage': storage_usage,
            'recent_reports': recent_reports,
            'alerts': active_alerts,
            'total_slots': total_slots,
            'used_slots': used_slots,
            'recent_activity': recent_activity,
            'storage_devices': storage_devices,
            'active_devices': active_devices,
            'total_aliquots': total_aliquots,
            'stored_aliquots': stored_aliquots,
        }
        return JsonResponse(stats)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


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
        
        # TODO: Implement actual report generation logic
        # For now, just mark as complete with sample data
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





# Sample Search and Find API
@login_required
def search_samples(request):
    """Search samples by various criteria"""
    query = request.GET.get('q', '')
    sample_type = request.GET.get('type', '')
    disposition = request.GET.get('disposition', '')
    
    samples = Sample.objects.all()
    
    if query:
        samples = samples.filter(
            Q(name__icontains=query) |
            Q(experiment__icontains=query)
        )
    
    if sample_type:
        samples = samples.filter(experiment__icontains=sample_type)
    
    if disposition:
        # Note: disposition is a computed property on Aliquot, not Sample
        # This would need to be implemented differently
        pass
    
    # Pagination
    paginator = Paginator(samples, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # AJAX request - return JSON
        sample_data = []
        for sample in page_obj:
            sample_data.append({
                'id': sample.id,
                'name': sample.name,
                'experiment': sample.experiment,
                'created_at': sample.created_at.isoformat() if hasattr(sample, 'created_at') else None,
            })
        
        return JsonResponse({
            'samples': sample_data,
            'total_count': samples.count(),
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
        })
    
    # Regular request - return HTML
    context = {
        'samples': page_obj,
        'query': query,
        'sample_type': sample_type,
        'disposition': disposition,
        'total_count': samples.count(),
    }
    return render(request, 'reports/sample_search.html', context)


# Storage Management Dashboard API
@login_required
def storage_dashboard(request):
    """Storage overview statistics"""
    try:
        # Device statistics
        total_devices = Device.objects.count()
        active_devices = Device.objects.filter(is_active=True).count()
        
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
        
        # Freezer status (mock data for now)
        freezer_status = []
        for device in Device.objects.filter(device_type='freezer')[:4]:
            freezer_status.append({
                'name': device.name,
                'temperature': -80.0,  # Mock temperature
                'status': 'operational',
                'capacity': f"{used_slots}/{total_slots}",
                'usage_percent': round((used_slots / total_slots * 100) if total_slots > 0 else 0)
            })
        
        stats = {
            'total_devices': total_devices,
            'active_devices': active_devices,
            'total_boxes': total_boxes,
            'used_boxes': used_boxes,
            'available_boxes': available_boxes,
            'total_slots': total_slots,
            'used_slots': used_slots,
            'freezer_status': freezer_status,
        }
        return JsonResponse(stats)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# Helper functions
def generate_sample_report_data(report_type, parameters):
    """Generate sample data for reports (placeholder)"""
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
    else:
        return {'message': 'Report data placeholder'}


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



