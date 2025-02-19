from django.urls import path
from . import views


urlpatterns = [
    path('samples/', views.index, name='index'),
    path('sample/', views.TempSampleView.as_view()),
]