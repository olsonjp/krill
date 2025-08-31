# Register your models here.
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import User, UserPreference, UserRole, Permission, UserAuditLog
from .forms import CustomUserCreationForm, CustomUserChangeForm


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    
    list_display = ('username', 'email', 'first_name', 'last_name', 'role_display', 'is_active', 'date_joined')
    list_filter = ('is_active', 'is_staff', 'is_superuser', 'date_joined', 'role__role')
    search_fields = ('username', 'first_name', 'last_name', 'email')
    ordering = ('username',)
    
    fieldsets = UserAdmin.fieldsets + (
        ('Additional Info', {'fields': ('role_display',)}),
    )
    readonly_fields = ('role_display',)
    
    def role_display(self, obj):
        if hasattr(obj, 'role'):
            role_colors = {
                'lab_admin': '#dc3545',  # Red
                'lab_manager': '#fd7e14',  # Orange
                'lab_member': '#28a745',  # Green
                'viewer': '#6c757d',  # Gray
            }
            color = role_colors.get(obj.role.role, '#6c757d')
            return format_html(
                '<span style="color: {}; font-weight: bold;">{}</span>',
                color,
                obj.role.get_role_display()
            )
        return 'No Role'
    role_display.short_description = 'Role'


@admin.register(UserPreference)
class UserPreferenceAdmin(admin.ModelAdmin):
    list_display = ('user', 'dark_mode', 'created_at')
    list_filter = ('dark_mode',)
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('created_at',)


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'department', 'lab_unit', 'created_at', 'updated_at')
    list_filter = ('role', 'department', 'lab_unit', 'created_at')
    search_fields = ('user__username', 'user__email', 'department', 'lab_unit')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'role')
        }),
        ('Organization', {
            'fields': ('department', 'lab_unit')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ('user', 'permission_type', 'content_type', 'object_id', 'granted_by', 'granted_at', 'expires_at', 'is_valid')
    list_filter = ('permission_type', 'content_type', 'granted_at', 'expires_at')
    search_fields = ('user__username', 'user__email', 'granted_by__username')
    readonly_fields = ('granted_at', 'is_valid')
    date_hierarchy = 'granted_at'
    
    fieldsets = (
        ('Permission Details', {
            'fields': ('user', 'permission_type', 'content_type', 'object_id')
        }),
        ('Grant Information', {
            'fields': ('granted_by', 'granted_at', 'expires_at')
        }),
        ('Status', {
            'fields': ('is_valid',)
        }),
    )
    
    def is_valid(self, obj):
        return obj.is_valid()
    is_valid.boolean = True
    is_valid.short_description = 'Valid'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'granted_by', 'content_type')


@admin.register(UserAuditLog)
class UserAuditLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'target_type', 'target_id', 'ip_address', 'timestamp')
    list_filter = ('action', 'target_type', 'timestamp', 'ip_address')
    search_fields = ('user__username', 'user__email', 'target_name', 'ip_address')
    readonly_fields = ('user', 'action', 'target_type', 'target_id', 'target_name', 'details', 'ip_address', 'user_agent', 'timestamp')
    date_hierarchy = 'timestamp'
    ordering = ('-timestamp',)
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'action', 'timestamp')
        }),
        ('Target Information', {
            'fields': ('target_type', 'target_id', 'target_name')
        }),
        ('Request Details', {
            'fields': ('ip_address', 'user_agent'),
            'classes': ('collapse',)
        }),
        ('Additional Details', {
            'fields': ('details',),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')
    
    def details_formatted(self, obj):
        if obj.details:
            formatted = []
            for key, value in obj.details.items():
                formatted.append(f"<strong>{key}:</strong> {value}")
            return mark_safe("<br>".join(formatted))
        return '-'
    details_formatted.short_description = 'Details'


# Custom admin site configuration
admin.site.site_header = "Krill Laboratory Management System"
admin.site.site_title = "Krill Admin"
admin.site.index_title = "Welcome to Krill Administration"