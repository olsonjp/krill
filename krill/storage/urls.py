from django.urls import path
from .views.list import StorageListView
from .views.detail import StorageDetailView

app_name = 'storage'

urlpatterns = [
    path('list/', StorageListView.as_view(), name='list'),
    path('detail/<str:type>/<int:pk>/', StorageDetailView.as_view(), name='detail'),
    # ... other existing urls ...
]