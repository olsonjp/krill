from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from .views import home, reports, settings
from person.admin import admin_site

urlpatterns = [
    path('admin/', admin_site.urls),
    path('', home, name='home'),
    path('reports/', reports, name='reports'),
    path('settings/', settings, name='settings'),
    path('sample/', include('sample.urls')),
    path('storage/', include('storage.urls')),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
]
