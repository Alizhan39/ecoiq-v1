"""
ml/finance — Finance structuring and instrument fit modules.

Public-facing name:  Islamic & Ethical Finance Fit
Internal use:        Instrument suitability scoring for project finance proposals

Language rules (all modules in this package):
  ✓ "potentially suitable for Islamic finance review"
  ✓ "requires qualified Shariah scholar / advisory board review"
  ✓ "indicative only — not a religious ruling"
  ✓ "may be compatible with Islamic finance principles"
  ✗ Do NOT write: Shariah-compliant, halal, haram, fatwa, religious ruling, forbidden
  ✗ Do NOT issue rulings or certifications of any kind
"""
from .islamic_finance_fit import (
    IslamicFinanceFitInput,
    IslamicFinanceFitResult,
    assess_islamic_finance_fit,
)

__all__ = [
    'IslamicFinanceFitInput',
    'IslamicFinanceFitResult',
    'assess_islamic_finance_fit',
]
