"""
ai_gateway/web_views.py — the EcoIQ assistant page.

The page is a thin shell: it renders the prompt box and the model selector,
then talks to `/api/ai/models/` and `/api/ai/chat/` over `fetch()` with the
session cookie and CSRF token. No model list, provider name, base URL or key
is baked into the template — the selector is populated at runtime from the
authenticated catalogue endpoint, so what the page can offer is exactly what
the server will accept.

Login-required for the same reason the API is: an AI generation costs a free
allowance, and anonymous access would let anyone drain it.
"""
from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def assistant(request):
    return render(request, 'ai_gateway/assistant.html', {
        # Only the URLs — every piece of model metadata arrives over the API.
        'models_url': '/api/ai/models/',
        'chat_url': '/api/ai/chat/',
    })
