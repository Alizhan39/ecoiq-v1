"""Twelve *research-only* governance domains for EcoIQ.

Internal taxonomy. Concepts and Quran references are thematic research leads,
not verified quotations, scholarly approvals, Shariah rulings or KPI formulas.
Never expose concept labels / Quran locators via public API. A public projection
contains only operational English domain titles and audit questions.

This intentionally does NOT add new IDs to islamic_knowledge.contracts.CONCEPTS,
register new formula definitions, or change the existing 20-KPI engine.
"""
from __future__ import annotations

from dataclasses import dataclass

from islamic_knowledge.catalog import QuranReference
from islamic_knowledge.contracts import CONCEPTS


@dataclass(frozen=True)
class ConceptTag:
    key: str
    arabic: str
    transliteration: str


@dataclass(frozen=True)
class GovernanceDomain:
    code: str
    operational_title: str
    name_ru: str
    tags: tuple[ConceptTag, ...]
    audit_questions: tuple[str, ...]
    quran_hints: tuple[QuranReference, ...] = ()
    research_status: str = "SCHOLAR_REVIEW_PENDING"

    def __post_init__(self) -> None:
        if (not self.code or not self.operational_title or not self.name_ru
                or not self.tags or not self.audit_questions):
            raise ValueError("Domain needs identifiers, concepts and operational questions.")
        if len({tag.key for tag in self.tags}) != len(self.tags):
            raise ValueError("Repeated concept in one domain.")
        if any(not all((tag.key, tag.arabic, tag.transliteration)) for tag in self.tags):
            raise ValueError("Concept metadata cannot be empty.")
        if any(not q.strip() for q in self.audit_questions):
            raise ValueError("Audit questions cannot be empty.")
        if any(not isinstance(ref, QuranReference) for ref in self.quran_hints):
            raise ValueError("Quran hints must be validated locators.")
        if self.research_status != "SCHOLAR_REVIEW_PENDING":
            raise ValueError("This research catalogue cannot claim religious approval.")

    @property
    def existing_contract_concepts(self) -> tuple[str, ...]:
        """Only these can link to existing knowledge contracts; never auto-activate."""
        return tuple(tag.key for tag in self.tags if tag.key in CONCEPTS)

    @property
    def awaiting_contract_mapping(self) -> tuple[str, ...]:
        """Unmapped tags are honest gaps, not permission to invent principles."""
        return tuple(tag.key for tag in self.tags if tag.key not in CONCEPTS)


_TAGS = {
    "adl": ConceptTag("adl", "العدل", "Adl"),
    "amanah": ConceptTag("amanah", "الأمانة", "Amanah"),
    "shura": ConceptTag("shura", "الشورى", "Shura"),
    "mal": ConceptTag("mal", "المال", "Mal"),
    "rizq": ConceptTag("rizq", "الرزق", "Rizq"),
    "qist": ConceptTag("qist", "القسط", "Qist"),
    "riba": ConceptTag("riba", "الربا", "Riba"),
    "gharar": ConceptTag("gharar", "الغرر", "Gharar"),
    "zakat": ConceptTag("zakat", "الزكاة", "Zakat"),
    "haqq": ConceptTag("haqq", "الحق", "Haqq"),
    "ihsan": ConceptTag("ihsan", "الإحسان", "Ihsan"),
    "maslaha": ConceptTag("maslaha", "المصلحة", "Maslaha"),
    "sadaqa": ConceptTag("sadaqa", "الصدقة", "Sadaqa"),
    "bayyinah": ConceptTag("bayyinah", "البينة", "Bayyinah"),
    "insaf": ConceptTag("insaf", "الإنصاف", "Insaf"),
    "ilm": ConceptTag("ilm", "العلم", "Ilm"),
    "tabayyun": ConceptTag("tabayyun", "التبين", "Tabayyun"),
    "tafakkur": ConceptTag("tafakkur", "التفكر", "Tafakkur"),
    "mizan": ConceptTag("mizan", "الميزان", "Mizan"),
    "israf": ConceptTag("israf", "الإسراف", "Israf"),
    "fasad": ConceptTag("fasad", "الفساد", "Fasad"),
    "rahma": ConceptTag("rahma", "الرحمة", "Rahma"),
    "masuliyya": ConceptTag("masuliyya", "المسؤولية", "Masuliyya"),
    "taharri_as_sidq": ConceptTag("taharri_as_sidq", "تحري الصدق", "Taharri as-Sidq"),
    "fiqh_al_maalat": ConceptTag("fiqh_al_maalat", "فقه المآلات", "Fiqh al-Maalat"),
    "taqwa": ConceptTag("taqwa", "التقوى", "Taqwa"),
    "muhasaba": ConceptTag("muhasaba", "المحاسبة", "Muhasaba"),
    "hikmah": ConceptTag("hikmah", "الحكمة", "Hikmah"),
}


def _domain(code: str, title: str, ru: str, concepts: tuple[str, ...],
            questions: tuple[str, ...], hints: tuple[tuple[int, ...], ...]) -> GovernanceDomain:
    return GovernanceDomain(
        code=code,
        operational_title=title,
        name_ru=ru,
        tags=tuple(_TAGS[key] for key in concepts),
        audit_questions=questions,
        quran_hints=tuple(QuranReference(*loc) for loc in hints),
    )


GOVERNANCE_DOMAINS: tuple[GovernanceDomain, ...] = (
    _domain("01", "Fair Governance", "Справедливое управление",
            ("adl", "amanah", "shura"),
            ("Are responsibilities and approval authorities documented?",
             "Are decisions reasoned, traceable and open to lawful challenge?"),
            ((4, 58), (4, 135), (42, 38))),
    _domain("02", "Economy and Capital", "Экономика и капитал",
            ("mal", "rizq", "qist"),
            ("Are property rights and contracts documented?",
             "Who receives the benefits and bears the financial risks?"),
            ((4, 29), (59, 7))),
    _domain("03", "Finance Contract Integrity", "Исламские финансы",
            ("riba", "gharar", "zakat"),
            ("Are finance terms, fees and risk allocations disclosed?",
             "Which compliance questions require qualified specialist review?"),
            ((2, 275), (2, 282), (9, 60))),
    _domain("04", "Work and Human Dignity", "Труд и человеческое достоинство",
            ("haqq", "ihsan", "amanah"),
            ("Are compensation, safety duties and contract terms documented?",
             "Can workers report grievances without retaliation?"),
            ((4, 29), (16, 90))),
    _domain("05", "Poverty and Social Wellbeing", "Бедность и общественное благополучие",
            ("maslaha", "sadaqa", "zakat"),
            ("Are eligibility and distribution criteria transparent?",
             "Is the actual outcome of assistance measured?"),
            ((2, 177), (9, 60))),
    _domain("06", "Courts and Dispute Resolution", "Суды и разрешение споров",
            ("adl", "bayyinah", "insaf"),
            ("Are evidence, hearing rights and procedural safeguards documented?",
             "Can errors be independently challenged and corrected?"),
            ((4, 135), (49, 6))),
    _domain("07", "Education and Science", "Образование и наука",
            ("ilm", "tabayyun", "tafakkur"),
            ("Can claims be traced to reproducible evidence?",
             "Are uncertainty and conflicting findings disclosed?"),
            ((17, 36), (20, 114))),
    _domain("08", "Nature and Resources", "Природа и ресурсы",
            ("mizan", "israf", "fasad"),
            ("Are resource flows recorded with units and baselines?",
             "Are environmental harms and remedies verified?"),
            ((7, 31), (30, 41), (55, 7, 9))),
    _domain("09", "Family and Future Generations", "Семья и будущие поколения",
            ("rahma", "haqq", "masuliyya"),
            ("Have vulnerable people and family impacts been considered?",
             "Are longer-term costs, benefits and risks disclosed?"),
            ((17, 23, 24), (31, 12, 19))),
    _domain("10", "Technology and AI Accountability", "Этика технологий и AI",
            ("amanah", "adl", "taharri_as_sidq"),
            ("Are model decisions explainable, reviewable and appealable?",
             "Are privacy, security and fabricated claims tested?"),
            ((4, 58), (49, 6))),
    _domain("11", "Public Decision Consequences", "Последствия государственных решений",
            ("maslaha", "fiqh_al_maalat"),
            ("Are alternative policies and affected groups compared?",
             "Are assumptions and unintended consequences monitored?"),
            ((42, 38), (59, 18))),
    _domain("12", "Moral Accountability", "Нравственная ответственность",
            ("taqwa", "muhasaba", "hikmah"),
            ("Are owners accountable for review and correction?",
             "Are material errors recorded and remediated?"),
            ((59, 18), (99, 7, 8))),
)

if tuple(domain.code for domain in GOVERNANCE_DOMAINS) != tuple(f"{i:02d}" for i in range(1, 13)):
    raise ValueError("Governance domain codes must be 01–12 in order.")


def domain_by_code(code: str) -> GovernanceDomain:
    """Internal lookup only. Returns draft descriptions; does not approve them."""
    for domain in GOVERNANCE_DOMAINS:
        if domain.code == code:
            return domain
    raise KeyError(code)


def operational_domain_rows() -> tuple[dict[str, object], ...]:
    """English-only operational projection; never exposes sacred-source hints.

    This is data preparation, NOT a public endpoint and NOT a moral score.
    """
    return tuple({
        "code": domain.code,
        "title": domain.operational_title,
        "audit_questions": domain.audit_questions,
        "kpi_links": (),
        "evidence_status": "NOT_ASSESSED",
    } for domain in GOVERNANCE_DOMAINS)
