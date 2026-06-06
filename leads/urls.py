from django.urls import path
from . import views

app_name = 'leads'

urlpatterns = [
    # Access request flow → Investor Readiness Report request
    path('',           views.request_access,  name='request_access'),
    path('thank-you/', views.thank_you,       name='thank_you'),
    path('success/',   views.success,         name='success'),  # legacy alias

    # EcoIQ Review Request flow
    path('review/',          views.request_review,  name='request_review'),
    path('review/success/',  views.review_success,  name='review_success'),

    # Profile claim flow
    path('claim/',         views.claim_profile_page,   name='claim_profile_page'),
    path('claim/submit/',  views.claim_profile_submit, name='claim_profile_submit'),
]
