"""
collaboration_rooms/services/ai_assist.py — Phase 27: optional, tightly
bounded AI assistance. This module can only ever READ room state and
return text — it has no import of, or access to, services.proposals /
services.rooms' mutating functions, so it is structurally incapable of
giving consent, accepting a next step, verifying a partner's claim, or
creating a project/action. Every call is instrumented in AI Observatory
(no second telemetry system) and every result is labelled as AI-generated
wherever it is displayed.

Reuses the existing agent_runtime_model_router.services.model_adapters.
AnthropicCompatibleAdapter — the same honesty discipline as PR9's
has_real_mail_transport(): if no real API key is configured, this
honestly reports that AI assistance is unavailable rather than fabricating
a summary.
"""
from agent_runtime_model_router.services.model_adapters import AnthropicCompatibleAdapter
from ai_observatory.services.recorder import finish_session, record_stage, start_session

from collaboration_rooms.services.summary import collaboration_summary


class AIAssistanceUnavailableError(Exception):
    pass


def _room_text_context(room):
    summary = collaboration_summary(room)
    messages = list(room.messages.filter(visibility='shared_with_room').order_by('created_at'))
    lines = [
        f'Opportunity: {summary["opportunity_title"]}', f'Organisation: {summary["organisation"]}',
        f'Room status: {summary["status"]}', '', 'Messages:',
    ]
    lines += [f'- [{m.organisation.name if m.organisation_id else "EcoIQ"}] {m.body}' for m in messages]
    lines += ['', 'Open questions:'] + [f'- {q}' for q in summary['open_questions']]
    return '\n'.join(lines)


def _run(room, instruction_suffix, *, actor):
    session = start_session(kind='collaboration_room_ai_assist', user=actor, human_review_required=True)
    with record_stage(session, 'ai_assist', instruction_suffix, category='llm') as info:
        prompt = f'{_room_text_context(room)}\n\n---\n\n{instruction_suffix}'
        result = AnthropicCompatibleAdapter().run({'prompt_text': prompt})
        info['success'] = result.status == 'success'
        info['metadata'] = {'failure_reason': result.failure_reason} if result.status != 'success' else {}
    finish_session(session, status='completed' if result.status == 'success' else 'failed', final_recommendation_status='not_applicable')

    if result.status != 'success':
        raise AIAssistanceUnavailableError(
            f'AI assistance is not available in this environment ({result.failure_reason or "no real model transport configured"}).'
        )
    from collaboration_rooms.services.timeline import record_event
    record_event(room, 'ai_assistance_used', actor=actor, notes=instruction_suffix, touch=False)
    return result.raw_text


def summarise_history(room, *, actor):
    return _run(room, 'Summarise this collaboration room\'s history in neutral, factual language. Do not invent facts not present above.', actor=actor)


def extract_open_questions(room, *, actor):
    return _run(room, 'List every open question or missing piece of information mentioned above, as a plain bullet list. Do not invent new questions.', actor=actor)


def draft_neutral_meeting_brief(room, *, actor):
    return _run(
        room,
        'Draft a short, neutral meeting brief (agenda + open items) for the next call between these parties, '
        'based only on the information above. Do not propose any commitment, funding, or partnership language.',
        actor=actor,
    )
