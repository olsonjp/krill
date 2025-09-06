from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import ReportTemplate, Report, ScheduledReport, Alert


@admin.register(ReportTemplate)
class ReportTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'report_type', 'is_active', 'created_by', 'created_at']
    list_filter = ['report_type', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    list_editable = ['is_active']

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'report_type', 'is_active')
        }),
        ('Template Configuration', {
            'fields': ('template_data',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ['name', 'template', 'status', 'format', 'created_by', 'created_at', 'file_size_display']
    list_filter = ['status', 'format', 'template__report_type', 'created_at']
    search_fields = ['name', 'description', 'created_by__username']
    readonly_fields = ['created_at', 'completed_at', 'file_size_display']
    list_editable = ['status']

    fieldsets = (
        ('Report Information', {
            'fields': ('name', 'description', 'template', 'status', 'format')
        }),
        ('Parameters & Results', {
            'fields': ('parameters', 'result_data')
        }),
        ('File Information', {
            'fields': ('file_path', 'file_size_display')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'completed_at', 'expires_at'),
            'classes': ('collapse',)
        }),
        ('User Information', {
            'fields': ('created_by',),
            'classes': ('collapse',)
        }),
    )

    def file_size_display(self, obj):
        if obj.file_size:
            if obj.file_size < 1024:
                return f"{obj.file_size} B"
            elif obj.file_size < 1024 * 1024:
                return f"{obj.file_size / 1024:.1f} KB"
            else:
                return f"{obj.file_size / (1024 * 1024):.1f} MB"
        return "N/A"
    file_size_display.short_description = 'File Size'


@admin.register(ScheduledReport)
class ScheduledReportAdmin(admin.ModelAdmin):
    list_display = ['name', 'template', 'frequency', 'is_active', 'last_run', 'next_run', 'created_by']
    list_filter = ['frequency', 'is_active', 'last_run', 'created_at']
    search_fields = ['name', 'description', 'created_by__username']
    readonly_fields = ['created_at', 'updated_at', 'last_run']
    list_editable = ['is_active']

    fieldsets = (
        ('Schedule Information', {
            'fields': ('name', 'description', 'template', 'frequency', 'is_active')
        }),
        ('Parameters & Recipients', {
            'fields': ('parameters', 'recipients')
        }),
        ('Execution History', {
            'fields': ('last_run', 'next_run'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ['title', 'severity', 'status', 'alert_type', 'created_at', 'status_actions']
    list_filter = ['severity', 'status', 'alert_type', 'created_at']
    search_fields = ['title', 'message', 'alert_type']
    readonly_fields = ['created_at', 'updated_at']
    list_editable = ['status']

    fieldsets = (
        ('Alert Information', {
            'fields': ('title', 'message', 'severity', 'status', 'alert_type')
        }),
        ('Target Information', {
            'fields': ('target_type', 'target_id'),
            'classes': ('collapse',)
        }),
        ('User Actions', {
            'fields': ('acknowledged_by', 'acknowledged_at', 'resolved_by', 'resolved_at'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def status_actions(self, obj):
        if obj.status == 'active':
            return format_html(
                '<a href="{}" class="button">Acknowledge</a>',
                reverse('admin:reports_alert_acknowledge', args=[obj.id])
            )
        elif obj.status == 'acknowledged':
            return format_html(
                '<a href="{}" class="button">Resolve</a>',
                reverse('admin:reports_alert_resolve', args=[obj.id])
            )
        return obj.get_status_display()
    status_actions.short_description = 'Actions'
