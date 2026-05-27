"""
EcoIQ Ingestion — Views.

GET  /ingest/              → form page (dark terminal UI)
POST /ingest/start/        → create IngestionJob, fire thread, return JSON {job_id}
GET  /ingest/status/<id>/  → poll JSON {status, progress_pct, progress_message, result_url, error}
GET  /ingest/job/<id>/     → job detail page (result viewer)
"""
import json

from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.views.decorators.http import require_POST

from .models import IngestionJob
from .pipeline import run_pipeline_in_thread


@staff_member_required(login_url='/login/')
def index(request):
    """Ingestion home: form + recent jobs list."""
    recent_jobs = IngestionJob.objects.select_related('result_company').order_by('-created_at')[:20]
    return render(request, 'ingestion/index.html', {'recent_jobs': recent_jobs})


@staff_member_required(login_url='/login/')
@require_POST
def start(request):
    """Create a job and fire the pipeline thread. Returns JSON."""
    company_name = request.POST.get('company_name', '').strip()
    if not company_name:
        return JsonResponse({'error': 'Company name is required.'}, status=400)

    url = request.POST.get('url', '').strip()

    job = IngestionJob.objects.create(company_name=company_name, url=url)
    run_pipeline_in_thread(job.pk)

    return JsonResponse({'job_id': job.pk})


@staff_member_required(login_url='/login/')
def status(request, job_id: int):
    """Lightweight polling endpoint."""
    job = get_object_or_404(IngestionJob, pk=job_id)

    result_url = None
    if job.result_company_id:
        from django.urls import reverse
        try:
            result_url = reverse('companies:detail', args=[job.result_company.slug])
        except Exception:
            result_url = f'/companies/{job.result_company.slug}/'

    return JsonResponse({
        'status':           job.status,
        'progress_pct':     job.progress_pct,
        'progress_message': job.progress_message,
        'result_url':       result_url,
        'result_company':   job.result_company.name if job.result_company else None,
        'error':            job.error_message or None,
        'duration':         job.duration_seconds,
    })


@staff_member_required(login_url='/login/')
def job_detail(request, job_id: int):
    """Detailed result page for a completed job."""
    job = get_object_or_404(
        IngestionJob.objects.select_related('result_company').prefetch_related('sources'),
        pk=job_id,
    )
    score_result     = job.score_result or {}
    extraction_result= job.extraction_result or {}
    search_result    = job.search_result or {}

    ctx = {
        'job':             job,
        'score_result':    score_result,
        'extraction':      extraction_result,
        'search_result':   search_result,
        'projects':        extraction_result.get('projects', []),
        'esg_signals':     extraction_result.get('esg_signals', {}),
        'data_gaps':       extraction_result.get('data_gaps', []),
        'gw_signals':      extraction_result.get('greenwashing_signals', []),
        'pillar_conf':     score_result.get('pillar_confidence', {}),
        'sources':         job.sources.all(),
    }
    return render(request, 'ingestion/job_detail.html', ctx)
