from django.urls import path
from .views.list import StorageListView
from .views.detail import StorageDetailView
from .views.create import StorageCreateView

app_name = 'storage'

urlpatterns = [
    path('list/', StorageListView.as_view(), name='list'),
    path('detail/<str:type>/<int:pk>/', StorageDetailView.as_view(), name='detail'),
    path('create/', StorageCreateView.as_view(), name='create'),
    # ... other existing urls ...
]