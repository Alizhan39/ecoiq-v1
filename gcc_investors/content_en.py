"""
gcc_investors/content_en.py — English copy for the 4 GCC investor pages.

Every page follows the same 15-section schema (see gcc_investors/views.py
docstring) so templates/gcc_investors/page_en.html can render all four
without page-specific template branches. Content itself must stay
country-specific per the GCC investor SEO spec ("must not be a doorway
page created by only replacing the country name") — do not copy a
paragraph from one country dict into another without rewriting it for
that country's actual positioning.

FACTUAL DISCIPLINE (spec: "Do not invent customers, revenue, signed
contracts, partnerships, certifications or investment commitments"):
  - capabilities.live only lists things genuinely built and running in
    this codebase today (league/companies scoring, screening, evidence,
    API, commercial platform, portfolio tools).
  - capabilities.prototype covers the mobile/desktop app (functional
    shell, not store-published) and embeddable badges.
  - capabilities.planned covers Arabic platform-wide UI, GCC hosting,
    marketplace/academy, and is explicitly NOT claimed as available now.
  - No country pilot, customer, or partnership is named as active
    anywhere in this file — "proposed" language only.
"""

_INVESTMENT_NOTICE = (
    'Information on this website is provided for business and strategic-partnership '
    'discussions only. It does not constitute an offer of securities, investment advice '
    'or a recommendation to invest. Any potential transaction would be subject to '
    'eligibility, due diligence, legal documentation and applicable regulatory requirements.'
)

# ── GCC Hub ──────────────────────────────────────────────────────────────────

HUB = {
    'meta': {
        'title': 'EcoIQ GCC Investors | AI Decision Intelligence Platform',
        'description': (
            'EcoIQ is an AI decision-intelligence platform for investors, banks, family offices '
            'and government-related institutions across the GCC. Explore country-specific '
            'positioning for Qatar, Saudi Arabia and Kuwait, current capabilities, and how to '
            'request an investor briefing.'
        ),
        'og_title': 'EcoIQ GCC Investors — AI Decision Intelligence Platform',
        'og_description': (
            'Sovereign investment analytics, ESG intelligence software and Islamic investment '
            'intelligence for qualified GCC investors and institutions.'
        ),
    },
    'hero': {
        'badge': 'GCC INVESTOR RELATIONS',
        'h1': 'AI decision intelligence for GCC investors and institutions',
        'subhead': (
            'EcoIQ evaluates companies, portfolios and public-sector decisions against '
            'environmental, ethical and Islamic-finance criteria, grounded in evidence rather '
            'than self-reported claims. This page is the starting point for banks, family '
            'offices, venture funds, corporate investors and government-related institutions '
            'across Qatar, Saudi Arabia and Kuwait considering a strategic relationship with EcoIQ.'
        ),
        'primary_cta_label': 'Request Investor Briefing',
        'secondary_cta_label': 'Book a Discovery Call',
    },
    'thesis': {
        'heading': 'Why decision intelligence, and why now',
        'body': [
            'Capital allocators across the GCC are under growing pressure to show that '
            'investment and procurement decisions account for environmental exposure, '
            'governance quality and — for a meaningful share of regional capital — Islamic '
            'finance compatibility. Most of that work is still done manually: analysts '
            'reading disclosures, sustainability reports and news coverage by hand, on '
            'timelines measured in weeks.',
            'EcoIQ is built to compress that timeline without compressing the rigour — '
            'AI-assisted analysis that always traces back to a cited, dated source, with '
            'every score carrying a stated confidence level rather than a false sense of '
            'certainty.',
        ],
    },
    'problem': {
        'heading': 'The problem with most ESG and screening tools',
        'body': [
            'Conventional ESG data providers score on disclosure volume, not verified '
            'outcome — a company that publishes a long sustainability report can outscore '
            'one that simply does the work quietly. Islamic-finance screening is often '
            'bolted on as a simple balance-sheet ratio check, with no link to the '
            'underlying evidence an investment committee would actually want to see.',
            'For GCC institutions specifically, almost no existing platform is built '
            'natively for the region — Arabic-language reporting, GCC data sources and '
            'regional hosting requirements are typically an afterthought, if addressed '
            'at all.',
        ],
    },
    'solution': {
        'heading': 'What EcoIQ does differently',
        'body': [
            'EcoIQ combines a deterministic, versioned scoring methodology (the EcoIQ '
            'Score) with an evidence layer that records source, publication date, and '
            'verification status for every material claim behind a company or country '
            'assessment, and a separate ethical/Islamic screening layer (built on EcoIQ\'s '
            'own Qur\'anic Decision Filter methodology) that is explicitly labelled as '
            'indicative — never presented as a formal fatwa or Shariah ruling.',
            'The result is a decision-support layer institutions can put in front of an '
            'investment committee, a risk function or a public-sector procurement panel, '
            'with every number traceable back to why it is what it is.',
        ],
    },
    'capabilities': {
        'heading': 'What is live today',
        'live': [
            'EcoIQ Score — a deterministic, versioned environmental and governance '
            'scoring engine covering public companies globally',
            'Ethical and Islamic (Qur\'anic Decision Filter) screening, with confidence '
            'levels and an explicit "insufficient evidence" state — never a false clean '
            'result',
            'AI-generated Investment Relevance Reports, grounded in cited evidence, with '
            'a human-reviewed publication workflow',
            'An evidence layer recording source, date and verification status behind '
            'material claims',
            'A versioned REST API (/api/v1/) with tiered entitlements, request logging '
            'and rate limits for institutional data licensing',
            'A commercial platform (plans, entitlements, API key management) supporting '
            'enterprise and government engagement tracks',
            'Portfolio and watchlist intelligence tools for tracking exposure across a '
            'set of holdings',
        ],
        'prototype': [
            'A native iOS, Android and Windows application — a functional technical '
            'shell (authentication, search, company profiles) is built; it has not yet '
            'been published to the App Store, Google Play or Microsoft Store',
            'Embeddable EcoIQ, ethical-screening and Islamic-screening badges for '
            'partner websites',
        ],
        'planned': [
            'A full Arabic-language platform interface (this page and its sibling GCC '
            'pages are Arabic today; the underlying product interface is not, yet)',
            'GCC regional data hosting and localisation',
            'A vetted, third-party Shariah advisory review of the Islamic screening '
            'methodology',
            'Project marketplace, Academy and Research product lines (catalogued in the '
            'commercial platform, not yet built)',
        ],
    },
    'use_cases': {
        'heading': 'How investors and institutions use EcoIQ',
        'items': [
            {
                'title': 'Portfolio screening',
                'body': (
                    'Apply environmental, ethical and Islamic-finance screens across an '
                    'existing portfolio or a shortlist under consideration, with every '
                    'exclusion traceable to a specific piece of evidence.'
                ),
            },
            {
                'title': 'Due-diligence acceleration',
                'body': (
                    'Use EcoIQ\'s evidence layer as a starting point for investment-committee '
                    'materials, cutting the manual research cycle without removing human '
                    'review from the final decision.'
                ),
            },
            {
                'title': 'Public-sector and sovereign programme evaluation',
                'body': (
                    'Evaluate the environmental, social and governance consequences of '
                    'capital-allocation decisions before they are finalised, with an '
                    'evidence-linked record for later audit.'
                ),
            },
            {
                'title': 'Islamic-finance compatible screening',
                'body': (
                    'Screen a company or sector against EcoIQ\'s Qur\'anic Decision Filter '
                    'methodology as one indicative input among others — not a substitute '
                    'for a qualified Shariah board\'s ruling.'
                ),
            },
        ],
    },
    'business_model': {
        'heading': 'Business and revenue model',
        'body': [
            'EcoIQ generates revenue from three connected sources: B2B2C data and API '
            'licensing for institutions building EcoIQ intelligence into their own '
            'workflows; direct subscriptions and enterprise licences for the platform '
            'itself; and scoped enterprise engagements — diagnostic assessments, '
            'time-boxed pilots, full deployments and annual licences — for banks, funds '
            'and government-related institutions.',
            'A project marketplace and paid research/education product line are '
            'catalogued for a future phase but are not active revenue lines today.',
        ],
    },
    'pricing': {
        'heading': 'Enterprise pricing model',
        'body': [
            'EcoIQ does not sell consumer-style monthly plans to institutional clients. '
            'Engagements are scoped and priced individually — an Enterprise Diagnostic '
            '(2–4 weeks), a 90-Day Enterprise Pilot, a full Enterprise Deployment, or an '
            'Annual Platform Licence — with government and sovereign programmes scoped '
            'separately at a higher tier reflecting the scale of a national or '
            'multi-institution deployment.',
            'Full price ranges, inclusions and the procurement process are published on '
            'the EcoIQ Enterprise Pricing page.',
        ],
        'cta_label': 'View Enterprise Pricing',
    },
    'scale': {
        'heading': 'Why the platform can scale',
        'body': [
            'The scoring, screening and evidence layers are built as a versioned, '
            'deterministic methodology, not a bespoke model per client — extending '
            'coverage to a new sector, market or data source is an engineering task on '
            'an existing architecture, not a rebuild.',
            'The API and commercial-entitlement layer already separate "what data a '
            'client is authorised to see" from "how the data is computed," which is the '
            'structural precondition for licensing the same intelligence to many '
            'institutions at once rather than building a one-off integration per client.',
        ],
    },
    'market_entry': {
        'heading': 'GCC market-entry plan',
        'intro': (
            'EcoIQ\'s regional plan is phased and deliberately conservative about what is '
            'claimed as already in place. No GCC pilot, deployment or partnership is '
            'active today.'
        ),
        'phases': [
            {'label': 'Phase 1 — Discovery',
             'body': 'Structured conversations with prospective GCC institutional partners to identify priority use cases, data availability and regulatory constraints.'},
            {'label': 'Phase 2 — Founding Partner pilots',
             'body': 'A limited number of scoped 90-day pilots with organisations that opt into the GCC Founding Partner programme (see below).'},
            {'label': 'Phase 3 — Regional product investment',
             'body': 'Arabic-language interface, GCC data localisation and regional hosting, prioritised by what Phase 1–2 partners actually need.'},
            {'label': 'Phase 4 — Broader institutional and government rollout',
             'body': 'Expansion beyond founding partners, subject to the outcomes and lessons of the earlier phases.'},
        ],
    },
    'founding_partner': {
        'heading': 'GCC Founding Partner programme',
        'body': [
            'A limited number of banks, investment institutions, corporates and '
            'government-related organisations across Qatar, Saudi Arabia and Kuwait can '
            'apply to become EcoIQ Founding Partners and help shape the platform\'s '
            'regional deployment.',
            'Founding Partner pricing is preferential versus the standard 90-Day '
            'Enterprise Pilot, and is available only to organisations that provide '
            'structured feedback, nominate a defined use case, and permit an anonymised '
            'case study, subject to approval — it is not an automatic discount.',
        ],
        'benefits': [
            'Preferential pilot pricing versus the standard 90-Day Enterprise Pilot',
            'Direct access to the EcoIQ product team',
            'Priority input into feature development',
            'Input into GCC data-localisation requirements',
            'Collaboration on the Arabic interface',
            'Preferential terms for expanding a successful pilot',
        ],
        'cta_label': 'Apply as a Founding Partner',
    },
    'governance': {
        'heading': 'Responsible AI, evidence and governance',
        'body': [
            'Every EcoIQ score is versioned to a stated methodology and carries a '
            'confidence level — insufficient evidence is reported as insufficient, never '
            'silently defaulted to a clean result. Draft and unpublished analysis is '
            'never exposed through the public site or API regardless of a caller\'s '
            'entitlement tier.',
            'The Islamic/ethical screening layer is explicitly labelled as an '
            'AI-assisted, indicative methodology inspired by Qur\'anic decision '
            'principles — not a fatwa, not a Shariah ruling, and not the output of an '
            'authorised religious governance process. Commercial relationships never '
            'influence a score, an evidence finding, or an analytical conclusion.',
        ],
    },
    'enquiry_intro': {
        'heading': 'Request an investor briefing',
        'subhead': (
            'Tell us about your organisation and area of interest. We will follow up to '
            'arrange a briefing — no payment is collected through this form.'
        ),
    },
    'faq': {
        'heading': 'Frequently asked questions',
        'items': [
            {
                'q': 'Is EcoIQ operating in the GCC today?',
                'a': (
                    'Not yet as an active deployment. This page describes EcoIQ\'s current '
                    'platform capabilities and its proposed approach to GCC market entry, '
                    'including a Founding Partner programme for early pilots.'
                ),
            },
            {
                'q': 'Is EcoIQ affiliated with any GCC government or sovereign fund?',
                'a': (
                    'No. EcoIQ is an independent company and is not affiliated with, '
                    'endorsed by, or acting on behalf of the governments, sovereign '
                    'wealth funds or public authorities of Qatar, Saudi Arabia or Kuwait.'
                ),
            },
            {
                'q': 'Does EcoIQ provide investment advice?',
                'a': (
                    'No. EcoIQ provides environmental, ethical and Islamic-finance-related '
                    'decision-support intelligence. It is not an investment adviser, '
                    'broker, exchange or Shariah authority, and nothing on this site is '
                    'investment advice or a recommendation to invest.'
                ),
            },
            {
                'q': 'Is the Islamic screening a Shariah certification?',
                'a': (
                    'No. It is EcoIQ\'s own AI-assisted, indicative methodology. Formal '
                    'Shariah compliance or certification requires assessment by qualified '
                    'independent Shariah advisers.'
                ),
            },
            {
                'q': 'How is pricing determined for GCC institutions?',
                'a': (
                    'The same way as elsewhere: scope, data volume, integrations, users '
                    'and security/hosting requirements — not a fixed consumer-style plan. '
                    'See Enterprise Pricing for the published ranges.'
                ),
            },
        ],
    },
    'legal': {
        'investment_notice': _INVESTMENT_NOTICE,
        'independence_notice': (
            'EcoIQ is an independent company. It is not affiliated with, sponsored by, '
            'endorsed by or acting on behalf of the governments, sovereign wealth funds '
            'or public authorities of Qatar, Saudi Arabia, Kuwait, or any other GCC state.'
        ),
    },
}


# ── Qatar ────────────────────────────────────────────────────────────────────

QATAR = {
    'meta': {
        'title': 'AI Startup Investment in Qatar | EcoIQ',
        'description': (
            'EcoIQ decision intelligence for Qatar\'s banks, asset managers, family '
            'offices and government-related institutions — financial intelligence, '
            'Islamic finance technology and sustainable capital allocation, with '
            'Arabic and GCC data localisation on the roadmap.'
        ),
        'og_title': 'EcoIQ — AI Decision Intelligence for Qatar\'s Investors',
        'og_description': (
            'AI investment intelligence, Islamic finance technology and ESG '
            'intelligence software built for Doha\'s financial institutions.'
        ),
    },
    'hero': {
        'badge': 'QATAR INVESTOR RELATIONS',
        'h1': 'AI decision intelligence for Qatar’s investors and institutions',
        'subhead': (
            'Qatar’s financial sector — banks, asset managers, family offices and '
            'sovereign-linked institutions — increasingly needs investment intelligence '
            'that accounts for environmental exposure and Islamic-finance compatibility '
            'together, not as two separate checks. EcoIQ is an AI decision-intelligence '
            'platform built for exactly that evaluation, with a GCC deployment plan that '
            'starts here.'
        ),
        'primary_cta_label': 'Request Investor Briefing',
        'secondary_cta_label': 'Book a Discovery Call',
    },
    'thesis': {
        'heading': 'Investment thesis: Qatar',
        'body': [
            'Doha has built one of the region’s deepest concentrations of asset '
            'managers, family offices and Islamic financial institutions, operating '
            'alongside a sovereign wealth base that already thinks in decades, not '
            'quarters. That combination rewards a platform that can evaluate '
            'sustainable capital allocation and Shariah-adjacent screening together, in '
            'a single evidence-linked workflow, rather than forcing institutions to '
            'reconcile two disconnected vendors.',
            'Qatar’s AI-startup investment environment is also maturing quickly, with '
            'institutional appetite for enterprise-grade, evidence-based intelligence '
            'tools rather than dashboard-only ESG products.',
        ],
    },
    'problem': {
        'heading': 'The market problem in Qatar',
        'body': [
            'Qatari banks and asset managers currently combine generic international '
            'ESG data (rarely built with GCC disclosure practices or Arabic-language '
            'sources in mind) with separate, often informal Islamic-finance screening '
            'carried out by internal teams or external advisers, on inconsistent '
            'criteria from one desk to the next.',
            'Neither side of that process is well evidenced — ESG scores rarely show '
            'their working, and screening decisions are rarely recorded in a way that '
            'would satisfy a later audit or a new committee member reviewing the file.',
        ],
    },
    'solution': {
        'heading': 'The EcoIQ solution for Qatar',
        'body': [
            'EcoIQ pairs its deterministic EcoIQ Score with an indicative Islamic '
            'screening layer (the Qur’anic Decision Filter methodology) in one '
            'evidence-linked record — every input traceable to a dated, cited source, '
            'and every screening outcome labelled with a confidence level rather than a '
            'false binary pass or fail.',
            'For institutions operating under Qatar Financial Centre or Qatar Central '
            'Bank oversight, that evidence trail is designed to support — not replace — '
            'existing internal governance and compliance processes.',
        ],
    },
    'capabilities': {
        'heading': 'What is live today',
        'live': [
            'EcoIQ Score — deterministic environmental and governance scoring for '
            'public companies globally, including companies Qatari institutions '
            'already hold or are evaluating',
            'Indicative Islamic (Qur’anic Decision Filter) screening with a stated '
            'confidence level',
            'AI-generated, evidence-grounded Investment Relevance Reports',
            'A versioned REST API for institutional data licensing',
            'Portfolio and watchlist intelligence tools',
        ],
        'prototype': [
            'A native mobile/desktop application (functional shell; not yet published '
            'to app stores)',
            'Embeddable ethical and Islamic-screening badges',
        ],
        'planned': [
            'Arabic-language platform interface',
            'Qatar/GCC data localisation and regional hosting',
            'Independent Shariah advisory review of the screening methodology',
            'A scoped Qatar pilot — proposed, not yet started (see market-entry plan '
            'below)',
        ],
    },
    'use_cases': {
        'heading': 'Use cases for Qatari banks, asset managers and family offices',
        'items': [
            {
                'title': 'Bank and asset-manager portfolio screening',
                'body': (
                    'Apply combined environmental and Islamic-finance screens across '
                    'listed holdings, with an evidence trail suitable for internal risk '
                    'and compliance review.'
                ),
            },
            {
                'title': 'Family-office due diligence',
                'body': (
                    'Accelerate the research phase of a new position with grounded, '
                    'cited evidence rather than a generic ESG data feed.'
                ),
            },
            {
                'title': 'Sustainable capital allocation',
                'body': (
                    'Evaluate the environmental exposure of a prospective allocation '
                    'before commitment, with a record that supports later reporting.'
                ),
            },
            {
                'title': 'Enterprise and government pilots',
                'body': (
                    'A scoped, time-boxed pilot against a defined portfolio, asset group '
                    'or decision process — see the Enterprise Pilot track on the pricing '
                    'page.'
                ),
            },
        ],
    },
    'business_model': {
        'heading': 'Business and revenue model',
        'body': [
            'In Qatar, as elsewhere, EcoIQ’s revenue comes from API/data licensing, '
            'platform subscriptions, and scoped enterprise engagements — not from '
            'transaction fees, brokerage, or asset-management activity. EcoIQ does not '
            'execute trades, hold assets, or take a position in any security it '
            'evaluates.',
        ],
    },
    'pricing': {
        'heading': 'Enterprise pricing model',
        'body': [
            'Qatari institutions engage through the same scoped commercial tracks as '
            'other markets — Enterprise Diagnostic, 90-Day Enterprise Pilot, Enterprise '
            'Deployment or Annual Platform Licence — priced individually against scope, '
            'not sold as a fixed monthly plan. See the GCC Founding Partner programme '
            'below for preferential early-pilot terms.',
        ],
        'cta_label': 'View Enterprise Pricing',
    },
    'scale': {
        'heading': 'Why the platform can scale in Qatar',
        'body': [
            'Because scoring and screening run on a shared, versioned methodology '
            'rather than a bespoke model per client, extending coverage to '
            'Qatar-listed and GCC-relevant companies is a data-and-configuration task '
            'on existing architecture — not a rebuild for the market.',
        ],
    },
    'market_entry': {
        'heading': 'Qatar market-entry plan',
        'intro': (
            'No Qatar deployment, pilot or partnership is active today. The plan below '
            'is proposed and phased.'
        ),
        'phases': [
            {'label': 'Phase 1 — Discovery',
             'body': 'Conversations with Doha-based banks, asset managers and family offices to confirm priority use cases and data access.'},
            {'label': 'Phase 2 — Founding Partner pilot',
             'body': 'A scoped 90-day pilot with one or more Qatar-based Founding Partners, against a defined portfolio or decision process.'},
            {'label': 'Phase 3 — Localisation',
             'body': 'Arabic interface and Qatar-relevant data sources, prioritised by pilot findings.'},
            {'label': 'Phase 4 — Broader Qatar rollout',
             'body': 'Expansion beyond founding partners, subject to pilot outcomes.'},
        ],
    },
    'founding_partner': {
        'heading': 'GCC Founding Partner programme',
        'body': [
            'Qatari banks, investment institutions, corporates and government-related '
            'organisations can apply to become EcoIQ Founding Partners, helping shape '
            'the platform for the Qatari market specifically.',
            'Founding Partner pricing is preferential versus the standard 90-Day '
            'Enterprise Pilot and is available only to a limited number of organisations '
            'that provide structured feedback, nominate a defined use case, and permit '
            'an anonymised case study, subject to approval.',
        ],
        'benefits': [
            'Preferential pilot pricing versus the standard 90-Day Enterprise Pilot',
            'Direct access to the EcoIQ product team',
            'Priority input into feature development',
            'Input into Qatar/GCC data-localisation requirements',
            'Collaboration on the Arabic interface',
            'Preferential terms for expanding a successful pilot',
        ],
        'cta_label': 'Apply as a Founding Partner',
    },
    'governance': {
        'heading': 'Responsible AI, evidence and governance',
        'body': [
            'Every score carries a stated methodology version and confidence level; '
            'insufficient evidence is reported as such, never defaulted to a clean '
            'result. The Islamic screening layer is explicitly indicative — not a '
            'fatwa, and not a substitute for review by a qualified Shariah board.',
        ],
    },
    'enquiry_intro': {
        'heading': 'Request an investor briefing',
        'subhead': (
            'Tell us about your organisation and area of interest. We will follow up to '
            'arrange a briefing — no payment is collected through this form.'
        ),
    },
    'faq': {
        'heading': 'Frequently asked questions — Qatar',
        'items': [
            {
                'q': 'Is EcoIQ active in Qatar today?',
                'a': (
                    'Not yet. This page describes current platform capabilities and a '
                    'proposed Qatar market-entry plan, including a Founding Partner pilot.'
                ),
            },
            {
                'q': 'Is EcoIQ affiliated with the Qatar Investment Authority or any Qatari government body?',
                'a': (
                    'No. EcoIQ is independent and is not affiliated with, endorsed by, or '
                    'acting on behalf of the Government of Qatar, the Qatar Investment '
                    'Authority, or any other Qatari public authority.'
                ),
            },
            {
                'q': 'Does EcoIQ’s Islamic screening replace Shariah board review?',
                'a': (
                    'No. It is an indicative, AI-assisted methodology. Formal Shariah '
                    'compliance requires assessment by qualified independent advisers.'
                ),
            },
            {
                'q': 'Can Qatari institutions start with a smaller engagement?',
                'a': (
                    'Yes — most organisations begin with an Enterprise Diagnostic or a '
                    'controlled 90-Day Pilot rather than a full deployment.'
                ),
            },
        ],
    },
    'legal': {
        'investment_notice': _INVESTMENT_NOTICE,
        'independence_notice': (
            'EcoIQ is an independent company. It is not affiliated with, sponsored by, '
            'endorsed by or acting on behalf of the Government of Qatar, the Qatar '
            'Investment Authority, or any other Qatari public authority.'
        ),
    },
}


# ── Saudi Arabia ─────────────────────────────────────────────────────────────

SAUDI = {
    'meta': {
        'title': 'Saudi AI and Vision 2030 Investment | EcoIQ',
        'description': (
            'EcoIQ decision intelligence for Saudi investors, holding companies and '
            'government-related entities — Vision 2030-aligned industrial, '
            'infrastructure and energy intelligence, portfolio and supply-chain '
            'analysis, with Arabic executive reporting on the roadmap.'
        ),
        'og_title': 'EcoIQ — AI Decision Intelligence for Saudi Investment and Transformation',
        'og_description': (
            'AI investment intelligence and ESG intelligence software for Riyadh’s '
            'investors and major Saudi holding groups.'
        ),
    },
    'hero': {
        'badge': 'SAUDI ARABIA INVESTOR RELATIONS',
        'h1': 'AI decision intelligence for Saudi investment and transformation',
        'subhead': (
            'Saudi Arabia’s Vision 2030 programme has made industrial, infrastructure '
            'and energy transformation a national priority, with major holding groups '
            'and government-related entities directing capital toward it at scale. EcoIQ '
            'is an AI decision-intelligence platform built to evaluate that capital '
            'allocation — environmentally, operationally and against supply-chain risk '
            '— before it is committed.'
        ),
        'primary_cta_label': 'Request Investor Briefing',
        'secondary_cta_label': 'Book a Discovery Call',
    },
    'thesis': {
        'heading': 'Investment thesis: Saudi Arabia',
        'body': [
            'Vision 2030 has created sustained institutional demand for technology that '
            'can evaluate industrial and infrastructure investments against '
            'transformation goals, not just financial return — energy transition '
            'exposure, supply-chain concentration risk, and governance quality all '
            'matter to a Riyadh-based investment committee or a major holding group in a '
            'way that a generic international ESG score does not capture well.',
            'That demand sits alongside a fast-growing Saudi appetite for AI-native '
            'enterprise software generally, which favours platforms — like EcoIQ — built '
            'around evidence and methodology rather than a black-box score.',
        ],
    },
    'problem': {
        'heading': 'The market problem in Saudi Arabia',
        'body': [
            'Industrial, energy and infrastructure investment decisions in Saudi Arabia '
            'increasingly require evaluating supply-chain and portfolio exposure across '
            'large, complex company structures — subsidiaries, joint ventures, and '
            'multi-tier suppliers — where most existing ESG and risk tools are built for '
            'single-entity analysis, not the group structures common among Saudi '
            'holding companies.',
            'Government-related entities in particular need evidence-linked '
            'documentation behind major capital decisions, which self-reported '
            'sustainability disclosures do not reliably provide.',
        ],
    },
    'solution': {
        'heading': 'The EcoIQ solution for Saudi Arabia',
        'body': [
            'EcoIQ’s scoring and evidence layers are built to trace environmental and '
            'governance exposure through a company’s structure and into related entities, '
            'and its portfolio-intelligence tools are designed for exactly the kind of '
            'multi-holding, cross-sector exposure common in Saudi industrial and '
            'infrastructure groups.',
            'Every finding carries a cited source and a confidence level, producing the '
            'kind of evidence-linked record a government-related entity or major holding '
            'group can defend later, not just at the point of decision.',
        ],
    },
    'capabilities': {
        'heading': 'What is live today',
        'live': [
            'EcoIQ Score — deterministic environmental and governance scoring, '
            'including energy, industrial and infrastructure sector coverage',
            'Portfolio and watchlist intelligence tools built for multi-holding exposure',
            'AI-generated, evidence-grounded Investment Relevance Reports',
            'A versioned REST API for institutional and enterprise data licensing',
            'A commercial platform supporting enterprise and government engagement '
            'tracks',
        ],
        'prototype': [
            'A native mobile/desktop application (functional shell; not yet published '
            'to app stores)',
            'Embeddable EcoIQ and ethical-screening badges',
        ],
        'planned': [
            'Arabic executive reporting and platform interface',
            'Saudi/GCC data localisation and regional hosting',
            'Deeper supply-chain and subsidiary-structure analysis, prioritised by '
            'pilot findings',
            'A scoped Saudi pilot — proposed, not yet started (see market-entry plan '
            'below)',
        ],
    },
    'use_cases': {
        'heading': 'Use cases for Saudi investors and major holding groups',
        'items': [
            {
                'title': 'Portfolio and supply-chain analysis',
                'body': (
                    'Evaluate environmental and governance exposure across a holding '
                    'group’s subsidiaries and major suppliers, not just the parent '
                    'entity.'
                ),
            },
            {
                'title': 'Vision 2030-aligned technology evaluation',
                'body': (
                    'Assess industrial, infrastructure and energy investments against '
                    'transformation and sustainability goals with an evidence-linked '
                    'record.'
                ),
            },
            {
                'title': 'Government and major holding-company deployments',
                'body': (
                    'A scoped enterprise pilot or deployment against a defined portfolio, '
                    'business unit or decision process — see the Enterprise Pilot and '
                    'Deployment tracks on the pricing page.'
                ),
            },
            {
                'title': 'Riyadh investor and family-office due diligence',
                'body': (
                    'Accelerate the evidence-gathering phase of a new position or a '
                    'portfolio review.'
                ),
            },
        ],
    },
    'business_model': {
        'heading': 'Business and revenue model',
        'body': [
            'In Saudi Arabia, as elsewhere, EcoIQ generates revenue from API/data '
            'licensing, platform subscriptions and scoped enterprise engagements — not '
            'from transaction fees or asset management. EcoIQ does not execute trades, '
            'hold assets, or take a position in any company or project it evaluates.',
        ],
    },
    'pricing': {
        'heading': 'Enterprise pricing model',
        'body': [
            'Saudi institutions and major holding groups engage through the same scoped '
            'commercial tracks used elsewhere — Enterprise Diagnostic, 90-Day Enterprise '
            'Pilot, Enterprise Deployment or Annual Platform Licence — with government '
            'and government-related deployments scoped at a separate tier reflecting the '
            'scale involved.',
        ],
        'cta_label': 'View Enterprise Pricing',
    },
    'scale': {
        'heading': 'Why the platform can scale in Saudi Arabia',
        'body': [
            'Coverage of a new sector, subsidiary structure or data source is an '
            'engineering and configuration task on EcoIQ’s existing, versioned '
            'methodology — not a rebuild — which matters given the scale and structural '
            'complexity of major Saudi industrial and holding groups.',
        ],
    },
    'market_entry': {
        'heading': 'Saudi Arabia market-entry plan',
        'intro': (
            'No Saudi deployment, pilot or partnership is active today. The plan below '
            'is proposed and phased.'
        ),
        'phases': [
            {'label': 'Phase 1 — Discovery',
             'body': 'Conversations with Riyadh-based investors, major holding groups and government-related entities to confirm priority use cases.'},
            {'label': 'Phase 2 — Founding Partner pilot',
             'body': 'A scoped 90-day pilot with one or more Saudi Founding Partners, against a defined portfolio, business unit or decision process.'},
            {'label': 'Phase 3 — Localisation and depth',
             'body': 'Arabic executive reporting and deeper supply-chain analysis, prioritised by pilot findings.'},
            {'label': 'Phase 4 — Broader Saudi rollout',
             'body': 'Expansion beyond founding partners, subject to pilot outcomes.'},
        ],
    },
    'founding_partner': {
        'heading': 'GCC Founding Partner programme',
        'body': [
            'Saudi banks, investment institutions, major holding groups and '
            'government-related organisations can apply to become EcoIQ Founding '
            'Partners, helping shape the platform for the Saudi market specifically.',
            'Founding Partner pricing is preferential versus the standard 90-Day '
            'Enterprise Pilot and is available only to a limited number of organisations '
            'that provide structured feedback, nominate a defined use case, and permit '
            'an anonymised case study, subject to approval.',
        ],
        'benefits': [
            'Preferential pilot pricing versus the standard 90-Day Enterprise Pilot',
            'Direct access to the EcoIQ product team',
            'Priority input into feature development',
            'Input into Saudi/GCC data-localisation requirements',
            'Collaboration on Arabic executive reporting',
            'Preferential terms for expanding a successful pilot',
        ],
        'cta_label': 'Apply as a Founding Partner',
    },
    'governance': {
        'heading': 'Responsible AI, evidence and governance',
        'body': [
            'Every score carries a stated methodology version and confidence level; '
            'insufficient evidence is reported as such, never defaulted to a clean '
            'result. Evidence provenance is designed to support internal governance and '
            'audit requirements typical of large Saudi holding and government-related '
            'structures.',
        ],
    },
    'enquiry_intro': {
        'heading': 'Request an investor briefing',
        'subhead': (
            'Tell us about your organisation and area of interest. We will follow up to '
            'arrange a briefing — no payment is collected through this form.'
        ),
    },
    'faq': {
        'heading': 'Frequently asked questions — Saudi Arabia',
        'items': [
            {
                'q': 'Is EcoIQ active in Saudi Arabia today?',
                'a': (
                    'Not yet. This page describes current platform capabilities and a '
                    'proposed Saudi market-entry plan, including a Founding Partner pilot.'
                ),
            },
            {
                'q': 'Is EcoIQ affiliated with the Saudi government or the Public Investment Fund?',
                'a': (
                    'No. EcoIQ is independent and is not affiliated with, endorsed by, or '
                    'acting on behalf of the Government of Saudi Arabia, the Public '
                    'Investment Fund, or any other Saudi public authority.'
                ),
            },
            {
                'q': 'Does EcoIQ claim formal Vision 2030 endorsement?',
                'a': (
                    'No. EcoIQ positions its capabilities as relevant to Vision '
                    '2030-aligned use cases; it does not claim government approval, '
                    'partnership or endorsement.'
                ),
            },
            {
                'q': 'Can Saudi institutions start with a smaller engagement?',
                'a': (
                    'Yes — most organisations begin with an Enterprise Diagnostic or a '
                    'controlled 90-Day Pilot rather than a full deployment.'
                ),
            },
        ],
    },
    'legal': {
        'investment_notice': _INVESTMENT_NOTICE,
        'independence_notice': (
            'EcoIQ is an independent company. It is not affiliated with, sponsored by, '
            'endorsed by or acting on behalf of the Government of Saudi Arabia, the '
            'Public Investment Fund, or any other Saudi public authority.'
        ),
    },
}


# ── Kuwait ───────────────────────────────────────────────────────────────────

KUWAIT = {
    'meta': {
        'title': 'Kuwait AI and FinTech Investment Opportunity | EcoIQ',
        'description': (
            'EcoIQ decision intelligence for Kuwait’s banks, investment companies and '
            'family offices — AI and FinTech investment due diligence, portfolio '
            'intelligence, and governance/evidence provenance, aligned with Kuwait '
            'Vision 2035 digital-transformation priorities.'
        ),
        'og_title': 'EcoIQ — AI Investment Intelligence for Kuwait’s Investors',
        'og_description': (
            'AI investment intelligence and ESG intelligence software for Kuwait’s '
            'banks, investment companies and family offices.'
        ),
    },
    'hero': {
        'badge': 'KUWAIT INVESTOR RELATIONS',
        'h1': 'AI investment intelligence for Kuwait’s investors and institutions',
        'subhead': (
            'Kuwait’s banks and investment companies operate in one of the region’s '
            'most established financial markets, now aligning with Kuwait Vision 2035’s '
            'digital-transformation priorities. EcoIQ is an AI decision-intelligence '
            'platform built for investment due diligence and portfolio intelligence, '
            'with governance and evidence provenance built in from the start.'
        ),
        'primary_cta_label': 'Request Investor Briefing',
        'secondary_cta_label': 'Book a Discovery Call',
    },
    'thesis': {
        'heading': 'Investment thesis: Kuwait',
        'body': [
            'Kuwait’s investment-company sector — long-established relative to '
            'newer regional fintech hubs — is under pressure to modernise its due-diligence '
            'and portfolio-monitoring tooling in step with Kuwait Vision 2035’s digital '
            'agenda, without abandoning the governance discipline the sector is built on.',
            'That combination favours evidence-first AI tools over dashboard-only '
            'products: Kuwaiti banks and investment companies need documentation they '
            'can defend to a board or regulator, not just a score.',
        ],
    },
    'problem': {
        'heading': 'The market problem in Kuwait',
        'body': [
            'Investment due diligence at Kuwaiti banks and investment companies still '
            'runs largely on manually assembled research, with environmental and '
            'governance screening often handled as a separate, later-stage check rather '
            'than integrated into the initial evaluation — which slows the process and '
            'leaves governance considerations less visible to the committee making the '
            'final call.',
            'Existing FinTech and portfolio tools available in the market are rarely '
            'built with evidence provenance as a first-class feature, making later audit '
            'or regulatory review harder than it needs to be.',
        ],
    },
    'solution': {
        'heading': 'The EcoIQ solution for Kuwait',
        'body': [
            'EcoIQ integrates environmental and governance screening into the same '
            'evidence-linked workflow as portfolio intelligence, so a Kuwaiti '
            'investment committee sees exposure and governance findings alongside the '
            'rest of the due-diligence picture rather than as a separate, bolted-on '
            'report.',
            'Every finding traces to a dated, cited source with a stated confidence '
            'level — designed specifically to hold up under later board or regulatory '
            'review.',
        ],
    },
    'capabilities': {
        'heading': 'What is live today',
        'live': [
            'EcoIQ Score — deterministic environmental and governance scoring for '
            'public companies globally',
            'Portfolio and watchlist intelligence tools',
            'AI-generated, evidence-grounded Investment Relevance Reports',
            'An evidence layer recording source, date and verification status',
            'A versioned REST API for institutional data licensing',
        ],
        'prototype': [
            'A native mobile/desktop application (functional shell; not yet published '
            'to app stores)',
            'Embeddable ethical-screening badges',
        ],
        'planned': [
            'Arabic-language platform interface',
            'Kuwait/GCC data localisation and regional hosting',
            'Deeper FinTech-sector due-diligence tooling, prioritised by pilot findings',
            'A scoped Kuwait pilot — proposed, not yet started (see market-entry plan '
            'below)',
        ],
    },
    'use_cases': {
        'heading': 'Use cases for Kuwaiti banks, investment companies and family offices',
        'items': [
            {
                'title': 'Investment due diligence',
                'body': (
                    'Integrate environmental and governance evidence directly into the '
                    'due-diligence workflow for a new position, rather than as a later, '
                    'separate check.'
                ),
            },
            {
                'title': 'Portfolio intelligence',
                'body': (
                    'Monitor exposure across existing holdings with an evidence-linked '
                    'record suitable for board and committee reporting.'
                ),
            },
            {
                'title': 'Governance and evidence provenance',
                'body': (
                    'Produce documentation behind a screening decision that can be '
                    'defended to a board, auditor or regulator later — not just cited at '
                    'the point of decision.'
                ),
            },
            {
                'title': 'Institutional pilots and strategic partnerships',
                'body': (
                    'A scoped, time-boxed pilot against a defined portfolio or decision '
                    'process — see the Enterprise Pilot track on the pricing page.'
                ),
            },
        ],
    },
    'business_model': {
        'heading': 'Business and revenue model',
        'body': [
            'In Kuwait, as elsewhere, EcoIQ generates revenue from API/data licensing, '
            'platform subscriptions and scoped enterprise engagements — not from '
            'transaction fees or asset management. EcoIQ does not execute trades, hold '
            'assets, or take a position in any security it evaluates.',
        ],
    },
    'pricing': {
        'heading': 'Enterprise pricing model',
        'body': [
            'Kuwaiti institutions engage through the same scoped commercial tracks used '
            'elsewhere — Enterprise Diagnostic, 90-Day Enterprise Pilot, Enterprise '
            'Deployment or Annual Platform Licence — priced against scope rather than '
            'sold as a fixed monthly plan.',
        ],
        'cta_label': 'View Enterprise Pricing',
    },
    'scale': {
        'heading': 'Why the platform can scale in Kuwait',
        'body': [
            'Because scoring, screening and evidence capture run on shared, versioned '
            'methodology, extending coverage to Kuwait-listed and GCC-relevant '
            'companies — and to deeper FinTech-sector due-diligence needs — is a '
            'configuration task on existing architecture, not a rebuild.',
        ],
    },
    'market_entry': {
        'heading': 'Kuwait market-entry plan',
        'intro': (
            'No Kuwait deployment, pilot or partnership is active today. The plan below '
            'is proposed and phased.'
        ),
        'phases': [
            {'label': 'Phase 1 — Discovery',
             'body': 'Conversations with Kuwaiti banks, investment companies and family offices to confirm priority use cases and data access.'},
            {'label': 'Phase 2 — Founding Partner pilot',
             'body': 'A scoped 90-day pilot with one or more Kuwait-based Founding Partners, against a defined portfolio or due-diligence process.'},
            {'label': 'Phase 3 — Localisation',
             'body': 'Arabic interface and Kuwait-relevant data sources, prioritised by pilot findings.'},
            {'label': 'Phase 4 — Broader Kuwait rollout',
             'body': 'Expansion beyond founding partners, subject to pilot outcomes.'},
        ],
    },
    'founding_partner': {
        'heading': 'GCC Founding Partner programme',
        'body': [
            'Kuwaiti banks, investment companies, corporates and government-related '
            'organisations can apply to become EcoIQ Founding Partners, helping shape '
            'the platform for the Kuwaiti market specifically.',
            'Founding Partner pricing is preferential versus the standard 90-Day '
            'Enterprise Pilot and is available only to a limited number of organisations '
            'that provide structured feedback, nominate a defined use case, and permit '
            'an anonymised case study, subject to approval.',
        ],
        'benefits': [
            'Preferential pilot pricing versus the standard 90-Day Enterprise Pilot',
            'Direct access to the EcoIQ product team',
            'Priority input into feature development',
            'Input into Kuwait/GCC data-localisation requirements',
            'Collaboration on the Arabic interface',
            'Preferential terms for expanding a successful pilot',
        ],
        'cta_label': 'Apply as a Founding Partner',
    },
    'governance': {
        'heading': 'Responsible AI, evidence and governance',
        'body': [
            'Every score carries a stated methodology version and confidence level; '
            'insufficient evidence is reported as such, never defaulted to a clean '
            'result. Evidence provenance — source, date, verification status — is '
            'designed as a first-class feature, not an afterthought, for institutions '
            'that need to defend a screening decision later.',
        ],
    },
    'enquiry_intro': {
        'heading': 'Request an investor briefing',
        'subhead': (
            'Tell us about your organisation and area of interest. We will follow up to '
            'arrange a briefing — no payment is collected through this form.'
        ),
    },
    'faq': {
        'heading': 'Frequently asked questions — Kuwait',
        'items': [
            {
                'q': 'Is EcoIQ active in Kuwait today?',
                'a': (
                    'Not yet. This page describes current platform capabilities and a '
                    'proposed Kuwait market-entry plan, including a Founding Partner pilot.'
                ),
            },
            {
                'q': 'Is EcoIQ affiliated with the Kuwaiti government or any state investment body?',
                'a': (
                    'No. EcoIQ is independent and is not affiliated with, endorsed by, or '
                    'acting on behalf of the Government of Kuwait, the Kuwait Investment '
                    'Authority, or any other Kuwaiti public authority.'
                ),
            },
            {
                'q': 'Does EcoIQ claim formal Vision 2035 endorsement?',
                'a': (
                    'No. EcoIQ positions its capabilities as relevant to Kuwait Vision '
                    '2035-aligned digital-transformation priorities; it does not claim '
                    'government approval, partnership or endorsement.'
                ),
            },
            {
                'q': 'Can Kuwaiti institutions start with a smaller engagement?',
                'a': (
                    'Yes — most organisations begin with an Enterprise Diagnostic or a '
                    'controlled 90-Day Pilot rather than a full deployment.'
                ),
            },
        ],
    },
    'legal': {
        'investment_notice': _INVESTMENT_NOTICE,
        'independence_notice': (
            'EcoIQ is an independent company. It is not affiliated with, sponsored by, '
            'endorsed by or acting on behalf of the Government of Kuwait, the Kuwait '
            'Investment Authority, or any other Kuwaiti public authority.'
        ),
    },
}

PAGES = {
    'hub': HUB,
    'qatar': QATAR,
    'saudi': SAUDI,
    'kuwait': KUWAIT,
}
