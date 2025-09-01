from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q
from ..models.sample import Sample
from ..models.aliquot import Aliquot, AliquotType, AliquotLocation
from ..models.source import Source


@login_required
def sample_search(request):
    """Search samples by various criteria"""
    query = request.GET.get('q', '')
    sample_type = request.GET.get('type', '')
    disposition = request.GET.get('disposition', '')
    
    # Start with all samples
    samples = Sample.objects.all()
    
    if query:
        samples = samples.filter(
            Q(name__icontains=query) |
            Q(experiment__icontains=query) |
            Q(notes__icontains=query)
        )
    
    if sample_type:
        samples = samples.filter(experiment__icontains=sample_type)
    
    # Pagination
    paginator = Paginator(samples, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # AJAX request - return JSON
        sample_data = []
        for sample in page_obj:
            sample_data.append({
                'id': sample.id,
                'name': sample.name,
                'experiment': sample.experiment,
                'created_at': sample.created_at.isoformat() if hasattr(sample, 'created_at') else None,
            })
        
        return JsonResponse({
            'samples': sample_data,
            'total_count': samples.count(),
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
        })
    
    # Regular request - return HTML
    context = {
        'samples': page_obj,
        'query': query,
        'sample_type': sample_type,
        'disposition': disposition,
        'total_count': samples.count(),
    }
    return render(request, 'sample/search.html', context)


@login_required
def aliquot_search(request):
    """Search aliquots by various criteria"""
    query = request.GET.get('q', '')
    sample_type = request.GET.get('type', '')
    disposition = request.GET.get('disposition', '')
    
    # Start with all aliquots
    aliquots = Aliquot.objects.select_related(
        'sample', 
        'aliquot_type'
    ).prefetch_related(
        'aliquotlocation_set__box'
    ).all()
    
    if query:
        aliquots = aliquots.filter(
            Q(sample__name__icontains=query) |
            Q(aliquot_type__name__icontains=query)
        )
    
    if sample_type:
        aliquots = aliquots.filter(aliquot_type__name__icontains=sample_type)
    
    if disposition:
        # Filter by disposition (this is a computed property, so we need to filter differently)
        # For now, we'll skip disposition filtering in the search
        pass
    
    # Pagination
    paginator = Paginator(aliquots, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # AJAX request - return JSON
        aliquot_data = []
        for aliquot in page_obj:
            aliquot_data.append({
                'id': aliquot.id,
                'name': str(aliquot),
                'sample_name': aliquot.sample.name,
                'aliquot_type': aliquot.aliquot_type.name if aliquot.aliquot_type else 'Unknown',
                'disposition': aliquot.disposition,
                'quantity': aliquot.quantity,
                'created_at': aliquot.created_at.isoformat() if hasattr(aliquot, 'created_at') else None,
            })
        
        return JsonResponse({
            'aliquots': aliquot_data,
            'total_count': aliquots.count(),
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
        })
    
    # Regular request - return HTML
    context = {
        'aliquots': page_obj,
        'query': query,
        'sample_type': sample_type,
        'disposition': disposition,
        'total_count': aliquots.count(),
    }
    return render(request, 'sample/search.html', context)
