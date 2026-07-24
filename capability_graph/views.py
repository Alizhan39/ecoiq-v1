"""
capability_graph/views.py — minimal staff-only browse/review UI. Not a
general graph explorer: just enough to see every organisation, its
evidence-backed capabilities and routes, and to let a human record
independent verification. Every mutation is staff-only, POST-only, and
requires a real actor, mirroring good_agents' PR5 governance views.
"""
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404, redirect, render

from capability_graph.models import CAPABILITY_CHOICES, Organisation, OrganisationCapability
from capability_graph.services.capabilities import VerificationNotAllowedError, verify_capability


@staff_member_required(login_url='/login/')
def organisation_list(request):
    organisations = Organisation.objects.prefetch_related('capabilities__public_routes').order_by('name')
    capability_filter = request.GET.get('capability', '')
    if capability_filter:
        organisations = organisations.filter(capabilities__capability=capability_filter).distinct()
    return render(request, 'capability_graph/organisation_list.html', {
        'organisations': organisations,
        'capability_choices': CAPABILITY_CHOICES,
        'active_capability': capability_filter,
    })


@staff_member_required(login_url='/login/')
def organisation_detail(request, pk):
    organisation = get_object_or_404(
        Organisation.objects.prefetch_related('capabilities__public_routes', 'capabilities__verified_by'),
        pk=pk,
    )
    return render(request, 'capability_graph/organisation_detail.html', {'organisation': organisation})


@staff_member_required(login_url='/login/')
def verify_capability_view(request, capability_pk):
    """Staff-only, POST-only — the only way an OrganisationCapability reaches 'independently_verified'."""
    edge = get_object_or_404(OrganisationCapability, pk=capability_pk)
    if request.method == 'POST':
        from django.contrib import messages
        try:
            verify_capability(edge, actor=request.user)
        except VerificationNotAllowedError as exc:
            messages.error(request, str(exc))
    return redirect('capability_graph:organisation_detail', pk=edge.organisation_id)
