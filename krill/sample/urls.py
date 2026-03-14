from django.urls import path
from django.views.generic import RedirectView
from .views.list import SampleListView
from .views.detail import ModelDetailView, AliquotDetailView
from .views.create import ModelCreateView
from .views.search import sample_search, aliquot_search
from .views.access_level_demo import sample_access_demo, aliquot_access_demo, access_level_info
from .views.views import SampleView

app_name = 'sample'

urlpatterns = [
    path('', SampleView.as_view(), name='sample'),
    path('list/', SampleListView.as_view(), name='sample_list'),
    path('search/', sample_search, name='sample_search'),
    path('detail/<str:type>/<int:pk>/', ModelDetailView.as_view(), name='detail'),
    path('aliquot/<int:pk>/', AliquotDetailView.as_view(), name='aliquot_detail'),
    # Backward-compatibility redirect: tube/<pk>/ -> aliquot/<pk>/
    path('tube/<int:pk>/', RedirectView.as_view(pattern_name='sample:aliquot_detail', permanent=False), name='tube_detail'),
    path('create/', ModelCreateView.as_view(), name='sample_create'),
    # Access level demo URLs
    path('access-demo/sample/<int:sample_id>/', sample_access_demo, name='access_demo_sample'),
    path('access-demo/aliquot/<int:aliquot_id>/', aliquot_access_demo, name='access_demo_aliquot'),
    path('access-level-info/', access_level_info, name='access_level_info'),
    # ... other existing urls ...
]
