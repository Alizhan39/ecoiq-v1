"""
ml/projects — Project readiness and pipeline intelligence modules.

Public-facing name: Project Readiness Score
Purpose: Assess how ready a transition project is for investor,
         development bank, or climate finance review.
"""
from .project_readiness import (
    ProjectReadinessInput,
    ProjectReadinessResult,
    assess_project_readiness,
)

__all__ = [
    'ProjectReadinessInput',
    'ProjectReadinessResult',
    'assess_project_readiness',
]
