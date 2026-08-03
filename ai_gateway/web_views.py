"""
ai_gateway/web_views.py — the EcoIQ assistant page.

The page is a thin shell: prompt box, answer mode, language, thread. It talks
to `/api/ai/chat/` over `fetch()` with the session cookie and CSRF token.

EcoIQ chooses the model, so the page deliberately has no model selector and
does not call `/api/ai/models/` at all. No model name, provider name, base URL,
temperature or API terminology appears anywhere in the rendered document, and
the request body it sends has no field capable of naming one.

Login-required for the same reason the API is: an AI generation costs a free
allowance, and anonymous access would let anyone drain it.
"""
from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def assistant(request):
    return render(request, 'ai_gateway/assistant.html', {
        'chat_url': '/api/ai/chat/',
    })
