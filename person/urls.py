from django.urls import path
from . import views

app_name = 'person'

urlpatterns = [
    # Theme toggle
    path('preferences/theme/', views.toggle_theme, name='toggle_theme'),
    # User management
    path('users/', views.user_list, name='user_list'),
    path('users/create/', views.create_user, name='create_user'),
    path('users/<int:user_id>/', views.user_detail, name='user_detail'),
    path('users/<int:user_id>/edit/', views.user_role_edit, name='user_role_edit'),
    # Password management
    path('change-password/', views.change_password, name='change_password'),
    # Permission management
    path('permissions/', views.permission_list, name='permission_list'),
    path('permissions/grant/', views.grant_permission, name='grant_permission'),
    path('permissions/bulk-grant/', views.bulk_grant_permission, name='bulk_grant_permission'),
    path('permissions/<int:permission_id>/revoke/', views.revoke_permission, name='revoke_permission'),
    # Audit logs
    path('audit-logs/', views.audit_log, name='audit_log'),
    # Data import
    path('data-import/', views.DataImportView.as_view(), name='data_import'),
    # API endpoints
    path('api/users/<int:user_id>/permissions/', views.user_permissions_api, name='user_permissions_api'),
    path('api/permissions/grant/', views.grant_object_permission_api, name='grant_object_permission_api'),
    path('api/permissions/revoke/', views.revoke_object_permission_api, name='revoke_object_permission_api'),
]
