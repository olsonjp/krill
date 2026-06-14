import csv
from datetime import date

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render

from ..models.consumable import Consumable
from .mixins import consumables_ordering_required


@login_required
@consumables_ordering_required
def consumable_reorder_list(request):
    items = (
        Consumable.objects.low_stock()
        .select_related('consumable_type', 'vendor', 'location__room')
        .order_by('vendor__name', 'name')
    )
    return render(request, 'consumables/reorder_list.html', {
        'items': items,
        'today': date.today(),
    })


@login_required
@consumables_ordering_required
def consumable_reorder_csv(request):
    items = (
        Consumable.objects.low_stock()
        .select_related('consumable_type', 'vendor', 'location__room')
        .order_by('vendor__name', 'name')
    )
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="reorder-list-{date.today()}.csv"'
    writer = csv.writer(response)
    writer.writerow([
        'Name', 'Type', 'Vendor', 'Catalog #', 'Quantity', 'Threshold', 'Unit', 'Location',
    ])
    for item in items:
        writer.writerow([
            item.name,
            item.consumable_type.name,
            item.vendor.name if item.vendor else '',
            item.catalog_number or '',
            item.quantity,
            item.low_stock_threshold,
            item.unit,
            str(item.location) if item.location else '',
        ])
    return response
