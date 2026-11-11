from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q
from ..models.sample import Sample
from ..models.aliquot import Aliquot, AliquotType, AliquotLocation
from ..models.source import Source
from ..widgets import aliquot_choice_label


@login_required
def sample_search(request):
    """Search samples by various criteria"""
    query = request.GET.get('q', '')
    sample_type = request.GET.get('type', '')
    disposition = request.GET.get('disposition', '')

    # Start with all samples
    samples = Sample.objects.select_related('source').order_by('name')

    if query:
        samples = samples.filter(
            Q(name__icontains=query) |
            Q(experiment__icontains=query) |
            Q(notes__icontains=query)
        )

    if sample_type:
        samples = samples.filter(experiment__icontains=sample_type)

    # Pagination
    page_size = 20 if request.GET.get('page_size') == '20' else 50
    paginator = Paginator(samples, page_size)
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
        'aliquot_type',
        'disposition',
    ).order_by('sample__name', 'id')

    if query:
        aliquots = aliquots.filter(
            Q(sample__name__icontains=query) |
            Q(aliquot_type__name__icontains=query)
        )

    if sample_type:
        aliquots = aliquots.filter(aliquot_type__name__icontains=sample_type)

    if disposition:
        # Filter by disposition directly on aliquot
        aliquots = aliquots.filter(
            disposition__disposition_type=disposition
        )

    # Pagination
    page_size = 20 if request.GET.get('page_size') == '20' else 50
    paginator = Paginator(aliquots, page_size)
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
                'disposition': aliquot.disposition.name if aliquot.disposition else '',
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


OPTION_LIMIT = 20


@login_required
def aliquot_options(request):
    """JSON for the Parent aliquot picker: aliquots matching what was typed.

    Every word typed must match something (sample name, type or passage), so "HeLa p8" finds the p8
    aliquots of HeLa. A word that is a number, with or without a leading #, also matches the aliquot
    number, and an aliquot with exactly that number is listed first. At most OPTION_LIMIT results come
    back, with `more` set when there are others, so the page never loads thousands of options.
    """
    query = request.GET.get('q', '').strip()
    if not query:
        return JsonResponse({'results': [], 'more': False})

    aliquots = Aliquot.objects.filter(deleted=False).select_related('sample', 'aliquot_type')
    words = query.split()
    for word in words:
        match = (
            Q(sample__name__icontains=word) |
            Q(aliquot_type__name__icontains=word) |
            Q(passage__icontains=word)
        )
        number = word.lstrip('#')
        if number.isdigit():
            match |= Q(pk=int(number))
        aliquots = aliquots.filter(match)

    exact = []
    only = words[0].lstrip('#') if len(words) == 1 else ''
    if only.isdigit():
        exact = list(aliquots.filter(pk=int(only)))
        aliquots = aliquots.exclude(pk=int(only))

    rows = exact + list(aliquots.order_by('sample__name', '-pk')[:OPTION_LIMIT + 1])
    return JsonResponse({
        'results': [{'id': a.pk, 'label': aliquot_choice_label(a)} for a in rows[:OPTION_LIMIT]],
        'more': len(rows) > OPTION_LIMIT,
    })
