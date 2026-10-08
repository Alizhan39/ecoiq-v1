"""EcoIQ Operating System core.

The OS is the product architecture. AI models and specialised workflows are
replaceable services behind these deterministic contracts; they are not the
top-level product model.
"""

from ecoiq_os.kernel import EcoIQOSCase, EcoIQOSDecision, evaluate_case

__all__ = ["EcoIQOSCase", "EcoIQOSDecision", "evaluate_case"]
