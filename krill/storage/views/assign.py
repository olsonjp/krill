from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.urls import reverse
from django.db import IntegrityError
from ..models.storage import Box
from sample.models.aliquot import Aliquot, AliquotLocation, AliquotDisposition, AliquotTube

@login_required
@require_http_methods(["POST"])
def assign_aliquot_to_box(request, box_id, row, column):
    """Assign an aliquot tube to a specific box position"""
    box = get_object_or_404(Box, pk=box_id)
    aliquot_id = request.POST.get('aliquot_id')
    tube_number = request.POST.get('tube_number')

    if not aliquot_id:
        messages.error(request, "Please select an aliquot to assign.")
        return redirect('storage:detail', type='box', pk=box_id)

    aliquot = get_object_or_404(Aliquot, pk=aliquot_id)

    # Check if position is already occupied
    if AliquotLocation.objects.filter(box=box, row=row, column=column).exists():
        messages.error(request, f"Position ({row}, {column}) is already occupied.")
        return redirect('storage:detail', type='box', pk=box_id)

    # If tube_number is specified, use that tube; otherwise use first available tube
    if tube_number:
        try:
            tube = aliquot.tubes.get(tube_number=int(tube_number))
        except AliquotTube.DoesNotExist:
            messages.error(request, f"Tube {tube_number} does not exist for this aliquot.")
            return redirect('storage:detail', type='box', pk=box_id)
    else:
        # Find first tube that's not already stored
        tube = aliquot.tubes.exclude(
            disposition__disposition_type='stored'
        ).first()
        if not tube:
            # All tubes are stored, use first tube
            tube = aliquot.tubes.first()
        if not tube:
            messages.error(request, "This aliquot has no tubes. Please create tubes first.")
            return redirect('storage:detail', type='box', pk=box_id)

    # Get stored disposition
    stored_disposition, _ = AliquotDisposition.objects.get_or_create(
        name='Stored',
        defaults={'disposition_type': 'stored'}
    )

    # Remove any existing location for this tube
    AliquotLocation.objects.filter(
        aliquot=aliquot,
        tube_number=tube.tube_number
    ).delete()

    # Create new location with race condition handling
    try:
        AliquotLocation.objects.create(
            aliquot=aliquot,
            box=box,
            row=row,
            column=column,
            tube_number=tube.tube_number
        )
    except IntegrityError:
        # Race condition: position was occupied between check and create
        messages.error(request, f"Position ({row}, {column}) is already occupied. Please try again.")
        return redirect('storage:detail', type='box', pk=box_id)

    # Update tube disposition to stored
    tube.disposition = stored_disposition
    tube.save()

    messages.success(request, f"Aliquot {aliquot.sample.name} tube #{tube.tube_number} assigned to position ({row}, {column}).")
    return redirect('storage:detail', type='box', pk=box_id)
