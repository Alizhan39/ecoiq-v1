"""
global_research/services/stewardship_screen.py — a lightweight, pre-scenario
stewardship screen for TechnologyCandidate/ManufacturerProfile rows.

This is NOT a second stewardship engine. `digital_twin.services.stewardship`
(the real, governed KPI engine) only operates on a real
`digital_twin.ModernisationScenario` — which a research candidate doesn't
become until a human approves a `create_supplier_neutral_scenario`
recommendation (see services/scenario_bridge.py). Before that point, this
module runs the SAME deterministic harm/vulnerability keyword screen
`digital_twin.services.stewardship` uses, directly against a candidate's
own text fields, so a Council/comparison pass has an honest early signal —
never a fabricated StewardshipAssessment row, since that model is
correctly scoped to a real scenario. Once the real ModernisationScenario
exists, the full governed engine takes over unmodified.
"""
HARM_KEYWORDS = {'injury', 'fatality', 'fatalities', 'death', 'displacement', 'exposure', 'harm', 'unsafe'}
VULNERABILITY_KEYWORDS = {'vulnerable', 'indigenous', 'resettlement', 'children', 'displaced', 'marginalised', 'marginalized'}


def _contains_any(text, keywords):
    lowered = (text or '').lower()
    return sorted(k for k in keywords if k in lowered)


def screen_technology_candidate(candidate):
    """Returns {'score': 0-100 or None, 'flags': [...], 'warning': bool}.
    Never persisted as a StewardshipAssessment — see module docstring."""
    harm_hits = _contains_any(candidate.worker_implications, HARM_KEYWORDS)
    vulnerability_hits = _contains_any(candidate.environmental_implications, VULNERABILITY_KEYWORDS)
    flags = []
    if harm_hits:
        flags.append(f'Harm-related language detected in worker_implications: {", ".join(harm_hits)}.')
    if vulnerability_hits:
        flags.append(f'Vulnerability-related language detected in environmental_implications: {", ".join(vulnerability_hits)}.')

    documented = bool(candidate.worker_implications or candidate.environmental_implications)
    if harm_hits:
        score = 0.0
    elif not documented:
        score = None
    else:
        score = 100.0 if not vulnerability_hits else 50.0

    return {'score': score, 'flags': flags, 'warning': bool(flags) or not documented}
