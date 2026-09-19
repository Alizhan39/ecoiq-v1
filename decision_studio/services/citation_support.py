"""Explicit claim support and access-safe rendering of stored source quotations."""
from copy import deepcopy

from django.core.exceptions import PermissionDenied

from evidence_memory.services.citations import INSUFFICIENT, assess_claim, resolve_citation


def add_claim_support(result):
    citations = {item['citation']['citation_id']: item['citation'] for item in result.get('supporting_evidence', []) if item.get('citation')}
    material = [result.get('executive_answer', '')] + result.get('key_findings', []) + result.get('risks', []) + result.get('opportunities', [])
    if result.get('recommendation'):
        material.append(result['recommendation'])
    result['claims'] = [assess_claim({'text': text, 'kind': 'conclusion', 'citation_ids': []}, citations)
                        for text in dict.fromkeys(material) if text]
    result['source_quotes'] = [assess_claim({'text': c['quote'], 'kind': 'source_quote', 'citation_ids': [cid]}, citations)
                               for cid, c in citations.items()]
    result['citation_policy_version'] = 1
    result['evidence_support_note'] = INSUFFICIENT
    return result


def result_for_reader(query, user):
    result = deepcopy(query.result)
    citations = {}
    removed = False
    result['supporting_evidence'] = [item if isinstance(item, dict) else {'excerpt': str(item)}
                                     for item in result.get('supporting_evidence', [])]
    for item in result.get('supporting_evidence', []):
        citation = item.get('citation')
        if citation is None:
            item['citation_unavailable'] = True
            continue
        try:
            resolved = resolve_citation(citation, user=user, project=query.project)
        except PermissionDenied:
            item.clear()
            item.update(citation_unavailable=True, excerpt='This source is unavailable under your current access permissions or failed its integrity check.')
            removed = True
        else:
            item['citation'] = resolved
            item['excerpt'] = resolved['quote']
            citations[resolved['citation_id']] = resolved
    result['source_quotes'] = [assess_claim({'text': c['quote'], 'kind': 'source_quote', 'citation_ids': [cid]}, citations)
                               for cid, c in citations.items()]
    if removed:
        # Revoking cross-project sharing also revokes cached derivatives.
        for key in ('claims', 'key_findings', 'ranking', 'risks', 'opportunities', 'visualizations', 'sources'):
            result[key] = []
        result.update(executive_answer=INSUFFICIENT, recommendation=INSUFFICIENT,
                      rationale='A cited source is no longer available.', uncertainty_notes=['A cited source is no longer available.'],
                      confidence_label='INSUFFICIENT_EVIDENCE', confidence_score=None)
    return result
