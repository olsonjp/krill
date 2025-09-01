from django.urls import path
from .views.list import SampleListView
from .views.detail import ModelDetailView, TubeDetailView
from .views.create import ModelCreateView
from .views.access_level_demo import sample_access_demo, aliquot_access_demo, access_level_info

app_name = 'sample'

urlpatterns = [
    path('list/', SampleListView.as_view(), name='list'),
    path('detail/<str:type>/<int:pk>/', ModelDetailView.as_view(), name='detail'),
    path('tube/<int:pk>/', TubeDetailView.as_view(), name='tube_detail'),
    path('create/', ModelCreateView.as_view(), name='create'),
    # Access level demo URLs
    path('access-demo/sample/<int:sample_id>/', sample_access_demo, name='access_demo_sample'),
    path('access-demo/aliquot/<int:aliquot_id>/', aliquot_access_demo, name='access_demo_aliquot'),
    path('access-level-info/', access_level_info, name='access_level_info'),
    # ... other existing urls ...
]