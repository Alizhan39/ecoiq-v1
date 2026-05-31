"""
ml/ethics — Ethical intelligence computation modules.

Orchestrated by ethical_score.py which is called from the API layer.
All modules operate on CompanyProfile field values; no external calls.

Public-facing terminology:
  stewardship, public benefit, long-term resilience, ethical alignment,
  evidence-based improvement, responsible modernisation.

Internal Maqasid mapping is in docs/ethical-intelligence-engine.md ONLY.
"""
from .ethical_score import compute_ethical_intelligence

__all__ = ['compute_ethical_intelligence']
