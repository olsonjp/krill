from django.urls import path
from .views.list import SampleListView
from .views.detail import ModelDetailView
from .views.create import ModelCreateView

app_name = 'sample'

urlpatterns = [
    path('list/', SampleListView.as_view(), name='list'),
    path('detail/<str:type>/<int:pk>/', ModelDetailView.as_view(), name='detail'),
    path('create/', ModelCreateView.as_view(), name='create'),
    # ... other existing urls ...
]