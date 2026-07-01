"""
LegacySafe AI — LLM provider abstraction.

The permission layer (services/permissions.py, services/retrieval.py) filters
context before any of this runs. Providers below only ever receive
`allowed_context` — content that already passed the deterministic access
check. Never pass blocked/restricted chunks into a provider's `generate()`.

Provider switching exists for cost, data sovereignty, and model flexibility —
not for permission logic, which never changes based on which provider is
plugged in. This hackathon MVP ships only MockProvider (fully deterministic,
no network call, no API key). The others are typed stubs describing the
integration seam for after the hackathon.
"""


class LLMProvider:
    name = 'base'

    def generate(self, prompt, allowed_context):
        raise NotImplementedError


class MockProvider(LLMProvider):
    """Deterministic, offline provider used for the hackathon demo. No API key, no network call."""
    name = 'mock'

    def generate(self, prompt, allowed_context):
        return {
            'provider': self.name,
            'answer': 'Deterministic mock response generated only from permission-filtered context.',
            'context_count': len(allowed_context),
        }


class OpenAICompatibleProvider(LLMProvider):
    """Roadmap: any OpenAI-compatible chat completions endpoint (OpenAI itself,
    BasedAPIs, Mistral, GLM, or a locally hosted open-weight model server)."""
    name = 'openai_compatible'

    def generate(self, prompt, allowed_context):
        raise NotImplementedError('Roadmap: plug in OpenAI-compatible endpoints such as BasedAPIs.')


class AnthropicProvider(LLMProvider):
    """Roadmap: native Anthropic Messages API."""
    name = 'anthropic'

    def generate(self, prompt, allowed_context):
        raise NotImplementedError('Roadmap: plug in the Anthropic Messages API.')
