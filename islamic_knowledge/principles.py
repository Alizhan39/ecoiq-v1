"""Draft EcoIQ questions inspired by source locators; not tafsir or rulings.

No source passage, authentication or reviewer is fabricated. Every definition
therefore fails the knowledge gate until a trusted adapter supplies reviewed,
versioned sources. Divine-name links remain inventory navigation only.
"""
from islamic_knowledge.catalog import QuranReference
from islamic_knowledge.contracts import PrincipleDefinition


def _draft(concept, statement, scope, refs, names=()):
    return PrincipleDefinition(
        id=f'ecoiq.{concept}.v1', concept=concept, version='1', statement=statement,
        scope=scope, source_ids=(),
        quran_references=tuple(QuranReference(*ref) for ref in refs), name_keys=names,
    )


DRAFT_PRINCIPLES = (
    _draft('hikmah', 'Compare alternatives, uncertainty, context and long-term consequences before choosing an action.',
           'Decision design; no wisdom score or claim to divine judgement.', ((2, 269), (16, 125)), ('al-hakim',)),
    _draft('adl', 'Examine who benefits, pays, bears risk, decides and can appeal; investigate mechanisms before alleging injustice.',
           'Distributional analysis; inequality alone is not causal proof.', ((4, 135), (5, 8), (16, 90)), ('al-adl', 'al-muqsit')),
    _draft('amanah', 'Record entrusted responsibilities, accountable owners and traceable commitments.',
           'Responsibility and governance.', ((4, 58),)),
    _draft('khalifah', 'Identify people, resources and future interests entrusted to the decision makers.',
           'Stewardship context.', ((2, 30),)),
    _draft('maqasid', 'Preserve separate evidence-backed benefits and harms for affected people.',
           'Impact records; interpretation and methodology need review.', ((5, 32),)),
    _draft('mizan', 'Check system balance and non-compensable harms using the existing Mizan contract.',
           'System balance; no replacement scoring formula.', ((55, 7, 9),)),
    _draft('israf', 'Measure avoidable resource loss with explicit units and evidence.',
           'Resource efficiency.', ((7, 31),)),
    _draft('fasad', 'Investigate mechanisms of compounding harm rather than infer guilt from an outcome.',
           'Systemic harm hypotheses.', ((30, 41),)),
    _draft('islah', 'Design a repair proposal and test its unintended consequences before implementation.',
           'Shared Islah change contract.', ((11, 88),)),
    _draft('ihsan', 'Seek evidence-backed improvement within safety and justice constraints.',
           'Constrained improvement; no fabricated savings.', ((16, 90),)),
    _draft('shura', 'Record affected-party participation, dissent and authorised human review.',
           'Consultation and decision accountability.', ((42, 38),)),
)
