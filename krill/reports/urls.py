from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    # Main Reports Dashboard
    path('', views.reports_dashboard, name='reports_dashboard'),

    # Dashboard Statistics
    path('dashboard/stats/', views.dashboard_stats, name='dashboard_stats'),

    # Report Generation
    path('generate/', views.generate_report, name='generate_report'),
    path('audit/', views.generate_audit_report, name='generate_audit_report'),
    path('list/', views.report_list, name='report_list'),
    path('detail/<int:report_id>/', views.report_detail, name='report_detail'),
    path('download/<int:report_id>/', views.download_report, name='download_report'),

    # Alert System
    path('alerts/', views.alert_list, name='alert_list'),
    path('alerts/<int:alert_id>/acknowledge/', views.acknowledge_alert, name='acknowledge_alert'),
    path('alerts/<int:alert_id>/resolve/', views.resolve_alert, name='resolve_alert'),
    path('alerts/create/', views.create_alert, name='create_alert'),


    # Storage Dashboard
    path('storage/dashboard/', views.storage_dashboard, name='storage_dashboard'),

    # Class-based views
    path('reports/', views.ReportListView.as_view(), name='report_list_cbv'),
    path('alerts/list/', views.AlertListView.as_view(), name='alert_list_cbv'),

]
