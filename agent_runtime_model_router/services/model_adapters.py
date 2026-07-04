"""
agent_runtime_model_router/services/model_adapters.py — provider-independent
model adapters, all sharing one `AdapterResult` contract.

Live adapters (OpenAI/Anthropic/Gemini/Azure OpenAI) check their credential
env var as the very first thing they do and return `status='failed',
failure_reason='missing_credentials'` cleanly — they never raise, and they
never fall back to fabricating a "successful" simulated result. Automated
tests only ever exercise this credential-absent path: no live network call
is ever made from this test suite.
"""
import json
from dataclasses import dataclass, field

from django.conf import settings


@dataclass
class AdapterResult:
    status: str                    # 'success' | 'failed'
    output: dict = None
    raw_text: str = ''
    failure_reason: str = ''       # '' | 'missing_credentials' | 'timeout' | 'rate_limit' | ...
    model_provider: str = ''
    model_name: str = ''
    estimated_input_tokens: int = None
    estimated_output_tokens: int = None
    actual_usage: dict = field(default_factory=dict)


class DeterministicTestAdapter:
    """Fully offline — replays the agent's own first golden test case verbatim."""
    provider = 'deterministic'

    def run(self, instruction):
        test_cases = instruction.get('test_cases') or {}
        realistic_cases = test_cases.get('realistic_test_cases') or []
        if not realistic_cases:
            return AdapterResult(
                status='failed', failure_reason='empty_response',
                model_provider=self.provider, model_name='deterministic-test-v1',
            )
        case = realistic_cases[0]
        return AdapterResult(
            status='success',
            output=case.get('expected_output', {}),
            raw_text=json.dumps(case),
            model_provider=self.provider, model_name='deterministic-test-v1',
            estimated_input_tokens=0, estimated_output_tokens=0,
        )


class SimulatedDemoAdapter:
    """
    Returns hand-authored fixture output supplied by the caller (e.g. the
    Boiler House #3 demo pipeline) — never invents output on its own.
    """
    provider = 'simulated'

    def run(self, instruction):
        fixture_output = instruction.get('fixture_output')
        if not fixture_output:
            return AdapterResult(
                status='failed', failure_reason='empty_response',
                model_provider=self.provider, model_name='simulated-demo-v1',
            )
        return AdapterResult(
            status='success',
            output=fixture_output,
            raw_text=json.dumps(fixture_output),
            model_provider=self.provider, model_name='simulated-demo-v1',
            estimated_input_tokens=0, estimated_output_tokens=0,
        )


class AnthropicCompatibleAdapter:
    provider = 'anthropic'

    def run(self, instruction):
        if not settings.ANTHROPIC_API_KEY:
            return AdapterResult(status='failed', failure_reason='missing_credentials', model_provider=self.provider)
        try:
            import anthropic
        except ImportError:
            return AdapterResult(status='failed', failure_reason='unsupported_capability', model_provider=self.provider)

        model_name = instruction.get('model_name', 'claude-opus-4-5')
        try:
            client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
            response = client.messages.create(
                model=model_name, max_tokens=1024,
                messages=[{'role': 'user', 'content': instruction.get('prompt_text', '')}],
            )
            text = response.content[0].text if response.content else ''
            usage = getattr(response, 'usage', None)
            return AdapterResult(
                status='success', raw_text=text,
                model_provider=self.provider, model_name=model_name,
                actual_usage={
                    'input_tokens': getattr(usage, 'input_tokens', None),
                    'output_tokens': getattr(usage, 'output_tokens', None),
                } if usage else {},
            )
        except Exception as exc:
            return AdapterResult(
                status='failed', failure_reason='timeout', raw_text=str(exc),
                model_provider=self.provider, model_name=model_name,
            )


class _RequestsBasedAdapter:
    """Shared HTTP-call skeleton for the 3 providers with no installed SDK."""
    provider = ''
    api_key_setting = ''
    default_model = ''

    def _endpoint(self, instruction):
        raise NotImplementedError

    def _headers(self, api_key):
        raise NotImplementedError

    def _payload(self, instruction, model_name):
        raise NotImplementedError

    def _parse_response(self, data):
        raise NotImplementedError

    def run(self, instruction):
        api_key = getattr(settings, self.api_key_setting, '')
        if not api_key:
            return AdapterResult(status='failed', failure_reason='missing_credentials', model_provider=self.provider)

        import requests
        model_name = instruction.get('model_name', self.default_model)
        try:
            response = requests.post(
                self._endpoint(instruction),
                headers=self._headers(api_key),
                json=self._payload(instruction, model_name),
                timeout=30,
            )
        except requests.exceptions.Timeout:
            return AdapterResult(status='failed', failure_reason='timeout', model_provider=self.provider, model_name=model_name)
        except requests.exceptions.RequestException as exc:
            return AdapterResult(status='failed', failure_reason='timeout', raw_text=str(exc), model_provider=self.provider, model_name=model_name)

        if response.status_code == 429:
            return AdapterResult(status='failed', failure_reason='rate_limit', model_provider=self.provider, model_name=model_name)
        if response.status_code >= 400:
            return AdapterResult(
                status='failed', failure_reason='timeout', raw_text=response.text[:500],
                model_provider=self.provider, model_name=model_name,
            )

        try:
            data = response.json()
        except ValueError:
            return AdapterResult(status='failed', failure_reason='invalid_json', model_provider=self.provider, model_name=model_name)

        text, usage = self._parse_response(data)
        return AdapterResult(
            status='success', raw_text=text, model_provider=self.provider, model_name=model_name,
            actual_usage=usage,
        )


class OpenAICompatibleAdapter(_RequestsBasedAdapter):
    provider = 'openai'
    api_key_setting = 'OPENAI_API_KEY'
    default_model = 'gpt-4o'

    def _endpoint(self, instruction):
        return 'https://api.openai.com/v1/chat/completions'

    def _headers(self, api_key):
        return {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}

    def _payload(self, instruction, model_name):
        return {
            'model': model_name,
            'messages': [{'role': 'user', 'content': instruction.get('prompt_text', '')}],
        }

    def _parse_response(self, data):
        text = data.get('choices', [{}])[0].get('message', {}).get('content', '')
        usage = data.get('usage', {})
        return text, usage


class GeminiCompatibleAdapter(_RequestsBasedAdapter):
    provider = 'gemini'
    api_key_setting = 'GEMINI_API_KEY'
    default_model = 'gemini-1.5-pro'

    def _endpoint(self, instruction):
        model_name = instruction.get('model_name', self.default_model)
        api_key = getattr(settings, self.api_key_setting, '')
        return f'https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}'

    def _headers(self, api_key):
        return {'Content-Type': 'application/json'}

    def _payload(self, instruction, model_name):
        return {'contents': [{'parts': [{'text': instruction.get('prompt_text', '')}]}]}

    def _parse_response(self, data):
        candidates = data.get('candidates', [])
        text = ''
        if candidates:
            parts = candidates[0].get('content', {}).get('parts', [])
            text = ''.join(p.get('text', '') for p in parts)
        usage = data.get('usageMetadata', {})
        return text, usage


class AzureOpenAICompatibleAdapter(_RequestsBasedAdapter):
    provider = 'azure_openai'
    api_key_setting = 'AZURE_OPENAI_API_KEY'
    default_model = 'gpt-4o'

    def run(self, instruction):
        if not getattr(settings, 'AZURE_OPENAI_ENDPOINT', ''):
            return AdapterResult(status='failed', failure_reason='missing_credentials', model_provider=self.provider)
        return super().run(instruction)

    def _endpoint(self, instruction):
        endpoint = settings.AZURE_OPENAI_ENDPOINT.rstrip('/')
        model_name = instruction.get('model_name', self.default_model)
        return f'{endpoint}/openai/deployments/{model_name}/chat/completions?api-version=2024-02-15-preview'

    def _headers(self, api_key):
        return {'api-key': api_key, 'Content-Type': 'application/json'}

    def _payload(self, instruction, model_name):
        return {'messages': [{'role': 'user', 'content': instruction.get('prompt_text', '')}]}

    def _parse_response(self, data):
        text = data.get('choices', [{}])[0].get('message', {}).get('content', '')
        usage = data.get('usage', {})
        return text, usage


ADAPTERS = {
    'deterministic': DeterministicTestAdapter,
    'simulated':     SimulatedDemoAdapter,
    'anthropic':     AnthropicCompatibleAdapter,
    'openai':        OpenAICompatibleAdapter,
    'gemini':         GeminiCompatibleAdapter,
    'azure_openai':   AzureOpenAICompatibleAdapter,
}


def get_adapter(provider):
    return ADAPTERS[provider]()
