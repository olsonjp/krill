from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from ..models.storage import Box
from ..models.site import Site
from django.db.models import Count, F, Q
from sample.models.aliquot import Aliquot

@login_required
def box_capacity(request):
    """Calculate and return the capacity information for all boxes."""
    boxes = Box.objects.annotate(
        total_slots=F('rows') * F('columns'),
        used_slots=Count('aliquot'),
        free_slots=F('rows') * F('columns') - Count('aliquot')
    ).values(
        'id',
        'name',
        'rack__name',
        'rack__shelf__name',
        'rack__shelf__device__name',
        'rack__shelf__device__site__name',
        'total_slots',
        'used_slots',
        'free_slots'
    )

    # Group by site for hierarchical view
    sites = {}
    for box in boxes:
        site_name = box['rack__shelf__device__site__name']
        device_name = box['rack__shelf__device__name']
        shelf_name = box['rack__shelf__name']
        rack_name = box['rack__name']
        
        if site_name not in sites:
            sites[site_name] = {'devices': {}, 'total_slots': 0, 'used_slots': 0, 'free_slots': 0}
        
        site = sites[site_name]
        if device_name not in site['devices']:
            site['devices'][device_name] = {'shelves': {}, 'total_slots': 0, 'used_slots': 0, 'free_slots': 0}
        
        device = site['devices'][device_name]
        if shelf_name not in device['shelves']:
            device['shelves'][shelf_name] = {'racks': {}, 'total_slots': 0, 'used_slots': 0, 'free_slots': 0}
        
        shelf = device['shelves'][shelf_name]
        if rack_name not in shelf['racks']:
            shelf['racks'][rack_name] = {'boxes': [], 'total_slots': 0, 'used_slots': 0, 'free_slots': 0}
        
        rack = shelf['racks'][rack_name]
        
        # Add box to rack
        rack['boxes'].append({
            'id': box['id'],
            'name': box['name'],
            'total_slots': box['total_slots'],
            'used_slots': box['used_slots'],
            'free_slots': box['free_slots']
        })
        
        # Update totals at each level
        rack['total_slots'] += box['total_slots']
        rack['used_slots'] += box['used_slots']
        rack['free_slots'] += box['free_slots']
        
        shelf['total_slots'] += box['total_slots']
        shelf['used_slots'] += box['used_slots']
        shelf['free_slots'] += box['free_slots']
        
        device['total_slots'] += box['total_slots']
        device['used_slots'] += box['used_slots']
        device['free_slots'] += box['free_slots']
        
        site['total_slots'] += box['total_slots']
        site['used_slots'] += box['used_slots']
        site['free_slots'] += box['free_slots']

    return JsonResponse({
        'sites': sites,
        'total_slots': sum(site['total_slots'] for site in sites.values()),
        'used_slots': sum(site['used_slots'] for site in sites.values()),
        'free_slots': sum(site['free_slots'] for site in sites.values())
    }) 