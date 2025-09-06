from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.http import require_http_methods
from person.decorators import has_object_access
from person.models import UserRole, UserAuditLog
from ..models.sample import Sample
from ..models.aliquot import Aliquot


@login_required
def sample_access_demo(request, sample_id):
    """
    Demo view showing access level restrictions for samples.
    This view demonstrates how access levels work in practice.
    """
    sample = get_object_or_404(Sample, id=sample_id)
    user_role = UserRole.get_or_create_for_user(request.user)

    # Check if user has access to this sample
    if not user_role.can_access_object(sample):
        UserAuditLog.log_action(
            user=request.user,
            action='view',
            target_type='Sample',
            target_id=sample_id,
            details={
                'access_denied': True,
                'sample_access_level': sample.access_level,
                'user_role': user_role.role
            },
            request=request
        )
        return HttpResponseForbidden(
            f"Access denied. This sample is restricted to {sample.get_access_level_display()}. "
            f"Your role ({user_role.get_role_display()}) does not have sufficient privileges."
        )

    # Log successful access
    UserAuditLog.log_action(
        user=request.user,
        action='view',
        target_type='Sample',
        target_id=sample_id,
        details={
            'access_granted': True,
            'sample_access_level': sample.access_level,
            'user_role': user_role.role
        },
        request=request
    )

    context = {
        'sample': sample,
        'user_role': user_role,
        'access_levels': Sample.ACCESS_LEVEL_CHOICES,
        'can_edit': user_role.has_permission('sample.edit'),
        'can_delete': user_role.has_permission('sample.delete'),
    }

    return render(request, 'sample/access_level_demo.html', context)


@login_required
def aliquot_access_demo(request, aliquot_id):
    """
    Demo view showing access level restrictions for aliquots.
    This view demonstrates how access levels work in practice.
    """
    aliquot = get_object_or_404(Aliquot, id=aliquot_id)
    user_role = UserRole.get_or_create_for_user(request.user)

    # Check if user has access to this aliquot
    if not user_role.can_access_object(aliquot):
        UserAuditLog.log_action(
            user=request.user,
            action='view',
            target_type='Aliquot',
            target_id=aliquot_id,
            details={
                'access_denied': True,
                'aliquot_access_level': aliquot.access_level,
                'user_role': user_role.role
            },
            request=request
        )
        return HttpResponseForbidden(
            f"Access denied. This aliquot is restricted to {aliquot.get_access_level_display()}. "
            f"Your role ({user_role.get_role_display()}) does not have sufficient privileges."
        )

    # Log successful access
    UserAuditLog.log_action(
        user=request.user,
        action='view',
        target_type='Aliquot',
        target_id=aliquot_id,
        details={
            'access_granted': True,
            'aliquot_access_level': aliquot.access_level,
            'user_role': user_role.role
        },
        request=request
    )

    context = {
        'aliquot': aliquot,
        'user_role': user_role,
        'access_levels': Aliquot.ACCESS_LEVEL_CHOICES,
        'can_edit': user_role.has_permission('aliquot.edit'),
        'can_delete': user_role.has_permission('aliquot.delete'),
    }

    return render(request, 'sample/aliquot_access_demo.html', context)


@login_required
@require_http_methods(["GET"])
def access_level_info(request):
    """
    API endpoint to get information about access levels and user permissions.
    """
    user_role = UserRole.get_or_create_for_user(request.user)

    # Get counts of objects by access level
    sample_counts = {}
    aliquot_counts = {}

    for level_code, level_name in Sample.ACCESS_LEVEL_CHOICES:
        sample_counts[level_code] = Sample.objects.filter(access_level=level_code).count()
        aliquot_counts[level_code] = Aliquot.objects.filter(access_level=level_code).count()

    # Get objects user can access
    accessible_samples = []
    accessible_aliquots = []

    for sample in Sample.objects.all()[:10]:  # Limit to first 10 for demo
        if user_role.can_access_object(sample):
            accessible_samples.append({
                'id': sample.id,
                'name': sample.name,
                'access_level': sample.access_level,
                'access_level_display': sample.get_access_level_display()
            })

    for aliquot in Aliquot.objects.all()[:10]:  # Limit to first 10 for demo
        if user_role.can_access_object(aliquot):
            accessible_aliquots.append({
                'id': aliquot.id,
                'name': str(aliquot),
                'access_level': aliquot.access_level,
                'access_level_display': aliquot.get_access_level_display()
            })

    data = {
        'user_role': user_role.role,
        'user_role_display': user_role.get_role_display(),
        'sample_counts': sample_counts,
        'aliquot_counts': aliquot_counts,
        'accessible_samples': accessible_samples,
        'accessible_aliquots': accessible_aliquots,
        'access_levels': {
            'admins_only': 'Lab Administrators only',
            'admins_managers': 'Lab Administrators and Managers',
            'all_members': 'All Lab Members'
        }
    }

    return JsonResponse(data)
