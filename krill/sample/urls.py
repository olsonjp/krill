from django.urls import path
from .views.views import SampleView
from .views.forms import SampleFormView
from .views.list import SampleListView

app_name = 'sample'

urlpatterns = [
    path('', SampleListView.as_view(), name='list'),
    path('samples/', SampleView.as_view(), name='Samples'),
    path('new/<str:type>/', SampleFormView.as_view(), name='new'),
]