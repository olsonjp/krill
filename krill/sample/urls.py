from django.urls import path
from . import views
from sample.views import SampleView


urlpatterns = [
    path('samples/', SampleView.as_view()),
]