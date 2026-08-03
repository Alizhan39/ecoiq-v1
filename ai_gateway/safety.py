"""
ai_gateway/safety.py — the internal content-safety classifier.

`AI_SAFETY_MODEL` (nvidia/nemotron-3.5-content-safety:free) is a *classifier*,
not a response model. Two independent guarantees keep it that way:

  * `routing.is_eligible()` filters it out of every routing chain, so it can
    never be selected to answer a user even if a task list named it;
  * nothing here returns generated prose — `screen()` returns a normalised
    `SafetyVerdict`, and the raw upstream body, its reasoning trace, its
    category payload and the provider's identity are all discarded at this
    boundary.

Screening is **selective**. A harmless text question never triggers it — that
would double every request's cost and latency for no benefit. It runs only for
the specific conditions in `triggers()`:

  * untrusted document instructions;
  * image uploads;
  * suspected prompt injection;
  * harmful-activity workflows;
  * staff-configured high-risk modules.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from django.conf import settings

from ai_gateway.exceptions import ProviderCallError

logger = logging.getLogger('ecoiq.ai_gateway.safety')

# ── Trigger names (internal; never shown to a user) ───────────────────────────
TRIGGER_UNTRUSTED_DOCUMENT = 'untrusted_document'
TRIGGER_IMAGE_UPLOAD = 'image_upload'
TRIGGER_SUSPECTED_INJECTION = 'suspected_injection'
TRIGGER_HARMFUL_ACTIVITY = 'harmful_activity'
TRIGGER_HIGH_RISK_MODULE = 'high_risk_module'

#: Phrases that characterise an attempt to override the assistant's
#: instructions. Deliberately narrow: this only decides whether to *screen*, it
#: never by itself blocks a request, so a false positive costs one extra
#: classifier call and nothing else.
_INJECTION_PATTERNS = (
    r'ignore (all |any |your )?(previous|prior|above|earlier) instructions',
    r'disregard (all |any |your )?(previous|prior|above) (instructions|rules)',
    r'you are now (a|an|no longer)',
    r'(reveal|show|print|repeat) (me )?(your |the )?(system )?prompt',
    r'developer mode',
    r'</?(system|instructions?)>',
    r'\bDAN\b mode',
)

#: Phrases that characterise a harmful-activity workflow. Same rule: this
#: selects for screening, it does not decide the outcome.
_HARMFUL_PATTERNS = (
    r'\b(synthesi[sz]e|manufactur\w*|make)\b.{0,40}\b(explosive|nerve agent|bioweapon)',
    r'\b(bypass|defeat|disable)\b.{0,30}\b(safety|security|authentication|detection)',
    r'\bmalware\b|\bransomware\b|\bkeylogger\b',
    r'\b(launder|laundering)\b.{0,20}\bmoney\b',
)

_INJECTION_RE = re.compile('|'.join(_INJECTION_PATTERNS), re.I)
_HARMFUL_RE = re.compile('|'.join(_HARMFUL_PATTERNS), re.I)


@dataclass(frozen=True)
class SafetyVerdict:
    """
    The only thing that leaves this module. `category` is a short normalised
    slug for structured logging — never the classifier's own words, never its
    reasoning, never the provider's payload.
    """
    screened: bool
    allowed: bool
    category: str = ''
    triggers: tuple[str, ...] = ()

    @property
    def blocked(self) -> bool:
        return self.screened and not self.allowed


ALLOWED = SafetyVerdict(screened=False, allowed=True)


def triggers(*, message: str = '', has_attachments: bool = False,
             has_images: bool = False, untrusted_document: bool = False,
             module: str = '') -> tuple[str, ...]:
    """Which screening conditions this request meets. Empty tuple == none."""
    found = []
    if has_images:
        found.append(TRIGGER_IMAGE_UPLOAD)
    if untrusted_document or (has_attachments and not has_images):
        found.append(TRIGGER_UNTRUSTED_DOCUMENT)
    if module and module in getattr(settings, 'AI_SAFETY_HIGH_RISK_MODULES', frozenset()):
        found.append(TRIGGER_HIGH_RISK_MODULE)
    if message:
        if _INJECTION_RE.search(message):
            found.append(TRIGGER_SUSPECTED_INJECTION)
        if _HARMFUL_RE.search(message):
            found.append(TRIGGER_HARMFUL_ACTIVITY)
    return tuple(found)


def should_screen(found: tuple[str, ...]) -> bool:
    return bool(found) and bool(getattr(settings, 'AI_SAFETY_ENABLED', True))


def screen(*, message: str, found: tuple[str, ...], request_id: str) -> SafetyVerdict:
    """
    Run the classifier. Never raises: if the classifier is unavailable the
    request proceeds unscreened rather than failing closed, because this is a
    *supplementary* check — the EcoIQ system prompt already instructs the model
    to refuse injected instructions, and taking the whole assistant down
    because a classifier is rate-limited would be a worse outcome.

    (Fail-closed applies to *model approval*, where a wrong guess spends money
    or exposes a paid model. Here a wrong guess only loses a second opinion.)
    """
    if not should_screen(found):
        return ALLOWED

    from ai_gateway.providers import get_provider
    from ai_gateway.registry import registry

    model_id = getattr(settings, 'AI_SAFETY_MODEL', '')
    snapshot = registry.get_snapshot()
    # The classifier must be in the validated registry — i.e. it passed the
    # same live zero-price and availability checks as every other model.
    approved = any(m.provider_model_id == model_id for m in snapshot.models)
    if not model_id or not approved:
        logger.warning('ai_gateway.safety_model_unavailable request_id=%s', request_id)
        return SafetyVerdict(screened=False, allowed=True, triggers=found)

    provider = get_provider('openrouter')
    if not provider.is_configured:
        return SafetyVerdict(screened=False, allowed=True, triggers=found)

    limit = int(getattr(settings, 'AI_SAFETY_MAX_INPUT_CHARS', 4000))
    prompt = (
        'Classify the following user content for safety. Answer with exactly '
        'one word: SAFE or UNSAFE.\n\n<content>\n'
        f'{message[:limit]}\n</content>'
    )

    try:
        response = provider.generate(
            model_id=model_id,
            messages=[{'role': 'user', 'content': prompt}],
            temperature=0.0,
            max_tokens=16,
            request_id=request_id,
        )
    except ProviderCallError as exc:
        logger.warning('ai_gateway.safety_check_failed category=%s request_id=%s',
                       exc.category, request_id)
        return SafetyVerdict(screened=False, allowed=True, triggers=found)
    except Exception:  # noqa: BLE001 — a classifier fault must not break chat
        logger.exception('ai_gateway.safety_check_crashed request_id=%s', request_id)
        return SafetyVerdict(screened=False, allowed=True, triggers=found)

    # Only the verdict is read. `response.content` is NOT retained, returned or
    # logged — that text is the classifier's raw output.
    verdict_unsafe = 'unsafe' in (response.content or '').strip().lower()[:32]

    logger.info('ai_gateway.safety_screened triggers=%s unsafe=%s request_id=%s',
                ','.join(found), verdict_unsafe, request_id)

    return SafetyVerdict(
        screened=True,
        allowed=not verdict_unsafe,
        category='unsafe_content' if verdict_unsafe else 'safe',
        triggers=found,
    )
