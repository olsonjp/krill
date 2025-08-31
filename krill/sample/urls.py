from django.urls import path
from .views.list import SampleListView
from .views.detail import ModelDetailView, TubeDetailView
from .views.create import ModelCreateView

app_name = 'sample'

urlpatterns = [
    path('list/', SampleListView.as_view(), name='list'),
    path('detail/<str:type>/<int:pk>/', ModelDetailView.as_view(), name='detail'),
    path('tube/<int:pk>/', TubeDetailView.as_view(), name='tube_detail'),
    path('create/', ModelCreateView.as_view(), name='create'),
    # ... other existing urls ...
]