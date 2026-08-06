"""
Anti-abuse protection for public form submissions.

Everything here runs BEFORE an AdminNotification, email, task, AI call or
external API request is created. `evaluate()` is the single entry point and is
deliberately side-effect-free apart from its own rate-limit counters, so a
caller can decide what to do with the verdict.

Layers, in the order they run:

    1. honeypot + form timing   (cheap, local)
    2. duplicate fingerprint    (cheap, cache + DB)
    3. rate limits              (cheap, cache)
    4. content heuristics       (cheap, local)
    5. Cloudflare Turnstile     (network, last — never called if already rejected)

Design rules this module follows:

  - Deterministic. No LLM, no model inference, explicit reason codes only.
  - Never uses nationality, religion, inferred ethnicity or name origin.
  - Never rejects a submission merely for using a mainstream free mail provider.
    Real EcoIQ enquiries come from gmail/outlook/yahoo constantly; the live spam
    used those same domains, so the domain carries no signal on its own.
  - Fails closed in production when Turnstile is configured but unreachable.
  - Never logs a full message, a full IP address or a Turnstile token.
"""
from .verdict import Decision, Verdict, Reason          # noqa: F401
from .engine import evaluate                            # noqa: F401
# Note: the `classify` submodule is deliberately NOT re-exported by name here.
# Binding `classify` to the function would shadow the module for anyone doing
# `from notifications.antispam import classify`, which is how both the engine
# and the management commands reach the thresholds.
from .classify import CLASSIFIER_VERSION, Corpus       # noqa: F401
from .fingerprint import submission_fingerprint, normalise_email, normalise_text  # noqa: F401
