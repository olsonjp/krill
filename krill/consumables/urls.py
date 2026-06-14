from django.urls import path
from django.views.generic import RedirectView

from .views.list import ConsumablesListView
from .views.detail import ConsumablesDetailView
from .views.create import ConsumablesCreateView
from .views.delete import consumable_delete
from .views.adjust import consumable_adjust
from .views.reorder import consumable_reorder_list, consumable_reorder_csv

app_name = 'consumables'

urlpatterns = [
    path('', RedirectView.as_view(pattern_name='consumables:list', query_string=True), name='consumables'),
    path('list/', ConsumablesListView.as_view(), name='list'),
    path('detail/<str:type>/<int:pk>/', ConsumablesDetailView.as_view(), name='detail'),
    path('create/', ConsumablesCreateView.as_view(), name='create'),
    path('consumable/<int:pk>/delete/', consumable_delete, name='delete'),
    path('consumable/<int:pk>/adjust/', consumable_adjust, name='adjust'),
    path('reorder/', consumable_reorder_list, name='reorder_list'),
    path('reorder/export.csv', consumable_reorder_csv, name='reorder_csv'),
]
