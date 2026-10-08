"""Content-bound review gates. Records are supplied by a trusted repository adapter.

These are validation contracts, not authentication: the caller must resolve
sources and authorised reviewers from its permission-checked provenance store.
Never construct approval receipts directly from request or model output.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from enum import Enum
from hashlib import sha256
import json
from typing import Mapping

from islamic_knowledge.catalog import QuranReference, divine_names


class SourceKind(str, Enum):
    QURAN = 'quran_text'
    TRANSLATION = 'translation'
    TAFSIR = 'tafsir'
    HADITH = 'hadith'
    SCHOLARLY_POSITION = 'scholarly_position'
    OPERATIONALISATION = 'ecoiq_operationalisation'
    AI_INFERENCE = 'ai_inference'


class Rights(str, Enum):
    OWNED = 'owned'
    LICENSED = 'licensed'
    PUBLIC_DOMAIN = 'public_domain'
    PERMISSION_PENDING = 'permission_pending'


CONCEPTS = ('khalifah', 'amanah', 'maqasid', 'adl', 'mizan', 'hikmah',
            'israf', 'fasad', 'islah', 'ihsan', 'shura')


def content_hash(text: str) -> str:
    """Hash exact UTF-8 bytes, without changing quotation whitespace."""
    return sha256(text.encode('utf-8')).hexdigest()


def _required(*values: str) -> None:
    if any(not isinstance(value, str) or not value.strip() for value in values):
        raise ValueError('Non-empty identifiers and attribution are required.')


@dataclass(frozen=True)
class SourceRecord:
    id: str
    kind: SourceKind
    work: str
    locator: str
    edition: str
    version: str
    passage: str
    digest: str
    language: str
    rights: Rights
    attribution: str
    authentication: str = 'unverified'
    quran_reference: QuranReference | None = None
    revoked: bool = False

    def __post_init__(self) -> None:
        _required(self.id, self.work, self.locator, self.edition, self.version,
                  self.passage, self.language, self.attribution)
        if not isinstance(self.kind, SourceKind) or not isinstance(self.rights, Rights):
            raise ValueError('Source kind and rights must use the declared enums.')
        if self.authentication not in ('verified', 'disputed', 'unverified'):
            raise ValueError('Unknown source authentication state.')
        if self.digest != content_hash(self.passage):
            raise ValueError('Passage does not match its content hash.')
        if self.quran_reference is not None and not isinstance(self.quran_reference, QuranReference):
            raise ValueError('Quran references must be validated records.')
        if self.kind in (SourceKind.QURAN, SourceKind.TRANSLATION):
            if self.quran_reference is None or self.locator != self.quran_reference.locator:
                raise ValueError('Quran/translation source needs an exact valid ayah locator.')
        if type(self.revoked) is not bool:
            raise ValueError('Revocation must be a boolean.')


@dataclass(frozen=True)
class ScholarlyPosition:
    id: str
    attribution: str
    statement: str
    scope: str
    source_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        _required(self.id, self.attribution, self.statement, self.scope)
        if not isinstance(self.source_ids, tuple) or not self.source_ids:
            raise ValueError('A scholarly position must cite immutable source IDs.')
        for identifier in self.source_ids:
            _required(identifier)


@dataclass(frozen=True)
class PrincipleDefinition:
    id: str
    concept: str
    version: str
    statement: str
    scope: str
    source_ids: tuple[str, ...]
    quran_references: tuple[QuranReference, ...] = ()
    name_keys: tuple[str, ...] = ()
    positions: tuple[ScholarlyPosition, ...] = ()
    sensitive: bool = False

    def __post_init__(self) -> None:
        _required(self.id, self.version, self.statement, self.scope)
        if self.concept not in CONCEPTS:
            raise ValueError(f'Unknown OS concept: {self.concept}')
        for values in (self.source_ids, self.quran_references, self.name_keys, self.positions):
            if not isinstance(values, tuple):
                raise ValueError('Knowledge collections must be immutable tuples.')
        if len(set(self.source_ids)) != len(self.source_ids):
            raise ValueError('Duplicate source IDs.')
        for identifier in self.source_ids:
            _required(identifier)
        if any(not isinstance(ref, QuranReference) for ref in self.quran_references):
            raise ValueError('Quran references must be validated records.')
        if any(key not in divine_names() for key in self.name_keys):
            raise ValueError('Unknown divine-name key in the declared enumeration.')
        if any(not isinstance(position, ScholarlyPosition) for position in self.positions):
            raise ValueError('Positions must be attributed scholarly records.')
        if len({position.id for position in self.positions}) != len(self.positions):
            raise ValueError('Duplicate scholarly position IDs.')
        if type(self.sensitive) is not bool:
            raise ValueError('Sensitivity must be a boolean.')

    @property
    def all_source_ids(self) -> tuple[str, ...]:
        return tuple(sorted(set(self.source_ids).union(
            *(position.source_ids for position in self.positions))))


def review_digest(definition: PrincipleDefinition, sources: Mapping[str, SourceRecord]) -> str:
    """Bind approval to every claim, position, source version and attribution."""
    payload = {
        'definition': asdict(definition),
        'sources': [asdict(sources[key]) for key in definition.all_source_ids],
    }
    return content_hash(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':')))


@dataclass(frozen=True)
class ReviewReceipt:
    reviewer_id: str
    role: str
    reviewed_at: date
    approved_digest: str
    revoked: bool = False

    def __post_init__(self) -> None:
        _required(self.reviewer_id)
        if self.role not in ('scholar', 'wellbeing'):
            raise ValueError('Unknown review role.')
        if type(self.reviewed_at) is not date or type(self.revoked) is not bool:
            raise ValueError('Review date and revocation must use declared types.')
        if len(self.approved_digest) != 64 or any(c not in '0123456789abcdef' for c in self.approved_digest):
            raise ValueError('Review needs a SHA-256 content digest.')


@dataclass(frozen=True)
class KnowledgeGate:
    definition_id: str
    definition_version: str
    content_digest: str | None
    reasons: tuple[str, ...]

    @property
    def ready(self) -> bool:
        return not self.reasons


@dataclass(frozen=True)
class KnowledgeBinding:
    """Immutable trusted inputs, re-assessed on every kernel evaluation."""
    definition: PrincipleDefinition
    sources: tuple[SourceRecord, ...] = ()
    receipts: tuple[ReviewReceipt, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.definition, PrincipleDefinition):
            raise ValueError('Binding needs a validated principle definition.')
        if not isinstance(self.sources, tuple) or not isinstance(self.receipts, tuple):
            raise ValueError('Binding collections must be immutable tuples.')
        if any(not isinstance(source, SourceRecord) for source in self.sources):
            raise ValueError('Binding needs validated source records.')
        if any(not isinstance(receipt, ReviewReceipt) for receipt in self.receipts):
            raise ValueError('Binding needs validated review receipts.')
        if len({source.id for source in self.sources}) != len(self.sources):
            raise ValueError('Duplicate source records in binding.')

    def assess(self) -> KnowledgeGate:
        return assess_definition(self.definition, {source.id: source for source in self.sources}, self.receipts)


def assess_definition(
    definition: PrincipleDefinition,
    sources: Mapping[str, SourceRecord],
    receipts: tuple[ReviewReceipt, ...] = (),
    *,
    as_of: date | None = None,
) -> KnowledgeGate:
    """Fail closed on gaps, changed/revoked content, rights or disagreement.

    `ready` permits consideration by the OS, never publication, certification,
    implementation, or an upgrade of the real-world causal evidence state.
    """
    today = date.today() if as_of is None else as_of
    reasons: list[str] = []
    if not definition.source_ids:
        reasons.append('MISSING_SOURCES')
    missing = [key for key in definition.all_source_ids if key not in sources]
    if missing:
        reasons.append('MISSING_SOURCE_RECORD')
    resolved = [sources[key] for key in definition.all_source_ids if key in sources]
    if any(sources[key].id != key for key in definition.all_source_ids if key in sources):
        reasons.append('SOURCE_ID_MISMATCH')
    if any(source.revoked for source in resolved):
        reasons.append('SOURCE_REVOKED')
    if any(source.rights == Rights.PERMISSION_PENDING for source in resolved):
        reasons.append('RIGHTS_PENDING')
    if any(source.authentication != 'verified' for source in resolved):
        reasons.append('SOURCE_AUTHENTICATION_REQUIRED')
    if any(source.kind == SourceKind.AI_INFERENCE for source in resolved):
        reasons.append('AI_INFERENCE_IS_NOT_RELIGIOUS_EVIDENCE')
    # An authored operationalisation cannot be its own religious evidence.
    religious = {SourceKind.QURAN, SourceKind.TRANSLATION, SourceKind.TAFSIR,
                 SourceKind.HADITH, SourceKind.SCHOLARLY_POSITION}
    if not any(source.kind in religious for source in resolved):
        reasons.append('MISSING_RELIGIOUS_SOURCE')
    cited_refs = {source.quran_reference for source in resolved if source.kind in religious}
    if any(ref not in cited_refs for ref in definition.quran_references):
        reasons.append('QURAN_REFERENCE_NOT_SOURCED')
    if len(definition.positions) > 1:
        reasons.append('SCHOLARLY_DISAGREEMENT_PRESENT')
    if definition.name_keys:
        # Inventory entries are all pending. A list/label never attests meaning.
        reasons.append('DIVINE_NAME_INTERPRETATION_REVIEW_REQUIRED')
    digest = None if missing else review_digest(definition, sources)
    valid_roles = {receipt.role for receipt in receipts
                   if not receipt.revoked and receipt.reviewed_at <= today
                   and digest is not None and receipt.approved_digest == digest}
    if 'scholar' not in valid_roles:
        reasons.append('SCHOLAR_REVIEW_REQUIRED')
    if definition.sensitive and 'wellbeing' not in valid_roles:
        reasons.append('WELLBEING_REVIEW_REQUIRED')
    return KnowledgeGate(definition.id, definition.version, digest, tuple(reasons))
