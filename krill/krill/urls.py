"""
URL configuration for krill project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from my_app import views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path
from django.views.decorators.csrf import csrf_exempt
from django.views.static import serve
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LogoutView
from .views.auth import KrillLoginView
from .views.home import HomeView, SettingsView, ReportsView, dashboard_stats
from .views.health import health_check
from person.views import toggle_theme
from .views.preferences import get_user_preferences, save_user_preferences
from person.admin import admin_site

admin.site.site_header = "Krill Admin"

urlpatterns = [
    path('admin/', admin_site.urls),
    path('health/', health_check, name='health_check'),
    path('login/', KrillLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),
    path('', HomeView.as_view(), name='home'),
    path('dashboard/stats/', dashboard_stats, name='dashboard_stats'),
    path('samples/', include('sample.urls')),
    path('storage/', include('storage.urls')),
    path('reports/', include('reports.urls')),
    path('settings/', SettingsView.as_view(), name='settings'),
    path('preferences/theme/', toggle_theme, name='toggle_theme'),
    path('preferences/user/', get_user_preferences, name='get_user_preferences'),
    path('preferences/save/', save_user_preferences, name='save_user_preferences'),
    path('users/', include('person.urls')),
    path('consumables/', include('consumables.urls')),
]
