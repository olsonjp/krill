from django.db import models
from django.conf import settings
from django.utils import timezone


class ReportTemplate(models.Model):
    REPORT_TYPE_CHOICES = [
        ('sample_inventory', 'Sample Inventory'),
        ('storage_capacity', 'Storage Capacity'),
        ('user_activity', 'User Activity'),
        ('aliquot_tracking', 'Aliquot Tracking'),
        ('storage_audit', 'Storage Audit'),
        ('custom', 'Custom Report'),
    ]
    
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    report_type = models.CharField(max_length=50, choices=REPORT_TYPE_CHOICES)
    template_data = models.JSONField(default=dict, help_text="JSON configuration for the report template")
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_templates')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['-created_at']


class Report(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('complete', 'Complete'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    FORMAT_CHOICES = [
        ('pdf', 'PDF'),
        ('csv', 'CSV'),
        ('json', 'JSON'),
        ('excel', 'Excel'),
    ]
    
    template = models.ForeignKey(ReportTemplate, on_delete=models.CASCADE, related_name='reports')
    name = models.CharField(max_length=200)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    format = models.CharField(max_length=10, choices=FORMAT_CHOICES, default='pdf')
    parameters = models.JSONField(default=dict, help_text="Parameters used to generate this report")
    result_data = models.JSONField(default=dict, blank=True, help_text="Generated report data")
    file_path = models.CharField(max_length=500, blank=True, null=True, help_text="Path to generated file")
    file_size = models.IntegerField(default=0, help_text="File size in bytes")
    error_message = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_reports')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.status})"

    def mark_complete(self, result_data=None, file_path=None, file_size=0):
        self.status = 'complete'
        if result_data:
            self.result_data = result_data
        if file_path:
            self.file_path = file_path
        if file_size:
            self.file_size = file_size
        self.completed_at = timezone.now()
        self.save()

    def mark_failed(self, error_message=None):
        self.status = 'failed'
        if error_message:
            self.error_message = error_message
        self.save()

    class Meta:
        ordering = ['-created_at']


class ScheduledReport(models.Model):
    FREQUENCY_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
    ]
    
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    template = models.ForeignKey(ReportTemplate, on_delete=models.CASCADE, related_name='scheduled_reports')
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES)
    parameters = models.JSONField(default=dict, help_text="Default parameters for the report")
    recipients = models.JSONField(default=list, help_text="List of email addresses to receive the report")
    is_active = models.BooleanField(default=True)
    last_run = models.DateTimeField(blank=True, null=True)
    next_run = models.DateTimeField(blank=True, null=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='scheduled_reports')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.frequency})"

    class Meta:
        ordering = ['-created_at']


class Alert(models.Model):
    SEVERITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('acknowledged', 'Acknowledged'),
        ('resolved', 'Resolved'),
        ('dismissed', 'Dismissed'),
    ]
    
    ALERT_TYPE_CHOICES = [
        ('storage', 'Storage'),
        ('sample', 'Sample'),
        ('system', 'System'),
        ('security', 'Security'),
        ('general', 'General'),
    ]
    
    title = models.CharField(max_length=200)
    message = models.TextField()
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='medium')
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPE_CHOICES, default='general')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    target_type = models.CharField(max_length=50, blank=True, null=True, help_text="Type of object this alert relates to")
    target_id = models.IntegerField(blank=True, null=True, help_text="ID of the object this alert relates to")
    acknowledged_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='acknowledged_alerts')
    acknowledged_at = models.DateTimeField(blank=True, null=True)
    resolved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='resolved_alerts')
    resolved_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} ({self.severity})"

    def acknowledge(self, user):
        self.status = 'acknowledged'
        self.acknowledged_by = user
        self.acknowledged_at = timezone.now()
        self.save()

    def resolve(self, user):
        self.status = 'resolved'
        self.resolved_by = user
        self.resolved_at = timezone.now()
        self.save()

    class Meta:
        ordering = ['-created_at']



