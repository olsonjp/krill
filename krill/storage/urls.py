from django.urls import path
from .views.forms import StorageFormView
from .views.list import StorageListView  # Import your list view
from .views.capacity import box_capacity

app_name = 'storage'  # Add namespace

urlpatterns = [
    path('', StorageListView.as_view(), name='list'),  # Add the list view URL
    path('new/<str:type>/', StorageFormView.as_view(), name='new'),
    path('capacity/', box_capacity, name='capacity'),
] 