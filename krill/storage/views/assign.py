from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.urls import reverse
from django.db import IntegrityError, transaction
from ..models.storage import Box
from sample.models.aliquot import Aliquot, AliquotLocation, AliquotDisposition

@login_required
@require_http_methods(["POST"])
def assign_aliquot_to_box(request, box_id, row, column):
    """Assign an aliquot to a specific box position"""
    box = get_object_or_404(Box, pk=box_id)
    aliquot_id = request.POST.get('aliquot_id')

    if not aliquot_id:
        messages.error(request, "Please select an aliquot to assign.")
        return redirect('storage:detail', type='box', pk=box_id)

    aliquot = get_object_or_404(Aliquot, pk=aliquot_id)

    # Get stored disposition
    stored_disposition, _ = AliquotDisposition.objects.get_or_create(
        name='Stored',
        defaults={'disposition_type': 'stored'}
    )

    # Create new location with race condition handling using atomic transaction
    try:
        with transaction.atomic():
            # Check if position is already occupied within transaction
            if AliquotLocation.objects.filter(box=box, row=row, column=column).exists():
                messages.error(request, f"Position ({row}, {column}) is already occupied.")
                return redirect('storage:detail', type='box', pk=box_id)

            # Remove any existing location for this aliquot first
            AliquotLocation.objects.filter(aliquot=aliquot).exclude(
                box=box, row=row, column=column
            ).delete()

            # Create location atomically
            AliquotLocation.objects.create(
                aliquot=aliquot,
                box=box,
                row=row,
                column=column,
            )

            # Update aliquot disposition to stored
            aliquot.disposition = stored_disposition
            aliquot.save()
    except IntegrityError:
        # Check if aliquot already has a location (OneToOne constraint)
        if AliquotLocation.objects.filter(aliquot=aliquot).exists():
            messages.error(
                request,
                "This aliquot already has a location. "
                "This may be due to a concurrent assignment. Please try again."
            )
        else:
            # Position must be occupied (unique_together: box, row, column)
            messages.error(
                request,
                f"Position ({row}, {column}) is already occupied. Please try again."
            )
        return redirect('storage:detail', type='box', pk=box_id)

    messages.success(request, f"Aliquot {aliquot.sample.name} assigned to position ({row}, {column}).")
    return redirect('storage:detail', type='box', pk=box_id)
