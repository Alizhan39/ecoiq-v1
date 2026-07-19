"""
agent_runtime_model_router/services/model_router.py — deterministic model
routing, in the same rule-table style as `ai_agent_council/services/routing.py`.
No ML, no scoring model, no randomness.

Every decision records not just the winning route but every other live
provider considered and why it wasn't chosen (`rejected_alternatives`) —
hardening requirement 3. Provider/model names here are illustrative
routing labels, not claims of real production tiering.
"""

LIVE_PROVIDERS = ['anthropic', 'openai', 'gemini', 'azure_openai']

DEFAULT_MODEL_BY_PROVIDER = {
    'anthropic':     'claude-opus-4-5',
    'openai':        'gpt-4o',
    'gemini':        'gemini-1.5-pro',
    'azure_openai':  'gpt-4o',
}

FALLBACK_MAP = {
    'anthropic':     'openai',
    'openai':        'anthropic',
    'gemini':        'openai',
    'azure_openai':  'anthropic',
}

LONG_CONTEXT_THRESHOLD_CHARS = 50_000


def default_model_for(provider):
    """The configured model for one provider, or None when the provider has
    no configured model. fix/router-fallback-model: the execution layer uses
    this when switching to a fallback provider, so a fallback adapter is
    always asked to run ITS OWN configured model — never the primary
    provider's model string (e.g. Anthropic being asked to run "gpt-4o",
    which can only ever fail). A None here means the fallback is skipped
    with an explicit, honest reason rather than attempted with a model the
    provider cannot serve."""
    return DEFAULT_MODEL_BY_PROVIDER.get(provider)


def _required_capability(requires_vision, requires_reasoning, context_length):
    if requires_vision:
        return 'vision'
    if requires_reasoning:
        return 'reasoning'
    if context_length > LONG_CONTEXT_THRESHOLD_CHARS:
        return 'long_context'
    return 'general'


def _reason_not_selected(provider, sensitivity_level, requires_vision, requires_reasoning, context_length):
    if provider == 'azure_openai':
        return f"Sensitivity level is '{sensitivity_level}', not 'high' — enterprise route not required."
    if provider == 'gemini':
        return (
            f"No vision requirement (requires_vision={requires_vision}) and context length "
            f"({context_length} chars) is within the standard threshold."
        )
    if provider == 'anthropic':
        return f"Task does not require heavy reasoning (requires_reasoning={requires_reasoning})."
    if provider == 'openai':
        return 'A more specific route applies (sensitivity, vision, reasoning, or context length).'
    return 'Not selected for this route.'


def select_model_route(agent_name, task_type, execution_mode, sensitivity_level='standard',
                        requires_vision=False, requires_reasoning=False, context_length=0,
                        cost_class='standard'):
    """
    Returns {selected_provider, selected_model, reason, sensitivity_level,
    required_capability, cost_class, rejected_alternatives, fallback_route}.
    """
    required_capability = _required_capability(requires_vision, requires_reasoning, context_length)

    if execution_mode == 'deterministic_test':
        return {
            'selected_provider': 'deterministic', 'selected_model': 'deterministic-test-v1',
            'reason': 'Deterministic automated tests always route to the deterministic test adapter.',
            'sensitivity_level': sensitivity_level, 'required_capability': required_capability,
            'cost_class': cost_class, 'rejected_alternatives': [], 'fallback_route': '',
        }

    if execution_mode == 'simulated_demo':
        return {
            'selected_provider': 'simulated', 'selected_model': 'simulated-demo-v1',
            'reason': 'Simulated demo runs always route to the simulated demo adapter.',
            'sensitivity_level': sensitivity_level, 'required_capability': required_capability,
            'cost_class': cost_class, 'rejected_alternatives': [], 'fallback_route': '',
        }

    # execution_mode == 'live'
    if sensitivity_level == 'high':
        chosen_provider = 'azure_openai'
        reason = 'Sensitive industrial data routes to the approved enterprise route.'
    elif requires_vision:
        chosen_provider = 'gemini'
        reason = 'Image input required — routed to a vision-capable model.'
    elif requires_reasoning:
        chosen_provider = 'anthropic'
        reason = 'Structured output plus financial/technical reasoning requires a reasoning-capable route.'
    elif context_length > LONG_CONTEXT_THRESHOLD_CHARS:
        chosen_provider = 'gemini'
        reason = 'Long document/report requires a long-context route.'
    else:
        chosen_provider = 'openai'
        reason = 'Default general-purpose live route — no elevated sensitivity, vision, reasoning or context requirement.'

    rejected_alternatives = [
        {
            'provider': provider,
            'model': DEFAULT_MODEL_BY_PROVIDER[provider],
            'reason_rejected': _reason_not_selected(
                provider, sensitivity_level, requires_vision, requires_reasoning, context_length,
            ),
        }
        for provider in LIVE_PROVIDERS if provider != chosen_provider
    ]

    return {
        'selected_provider': chosen_provider,
        'selected_model': DEFAULT_MODEL_BY_PROVIDER[chosen_provider],
        'reason': reason,
        'sensitivity_level': sensitivity_level,
        'required_capability': required_capability,
        'cost_class': cost_class,
        'rejected_alternatives': rejected_alternatives,
        'fallback_route': FALLBACK_MAP[chosen_provider],
    }
