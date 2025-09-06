from django.urls import path
from .views.list import StorageListView
from .views.detail import StorageDetailView
from .views.create import StorageCreateView
from .views.capacity import box_capacity
from .views.views import StorageView

app_name = 'storage'

urlpatterns = [
    path('', StorageView.as_view(), name='storage'),
    path('list/', StorageListView.as_view(), name='storage_list'),
    path('devices/', StorageListView.as_view(), name='device_list'),
    path('boxes/', StorageListView.as_view(), name='box_list'),
    path('detail/<str:type>/<int:pk>/', StorageDetailView.as_view(), name='detail'),
    path('create/', StorageCreateView.as_view(), name='create'),
    path('capacity/', box_capacity, name='capacity'),
    # ... other existing urls ...
]
