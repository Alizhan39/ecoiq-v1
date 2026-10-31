/**
 * content — every claim the public-sector pages make, in one place.
 *
 * WHY THE COPY IS A DATA MODULE AND NOT JSX
 * -----------------------------------------
 * Because it is the part that can be wrong. A procurement page is read by
 * someone whose job is to hold a supplier to what it wrote, so each claim here
 * was checked against the repository before it was typed, and the check is
 * recorded beside it. Keeping them together means the next person to edit a
 * line can see what it rests on, and core/tests_public_sector.py can scan this
 * file for claims that must never appear.
 *
 * THE RULE THIS FILE FOLLOWS
 * --------------------------
 * A service is work EcoIQ can be engaged to do. A platform capability is
 * software that exists in this repository today. They are stated separately,
 * because conflating them is how a supplier ends up contracted to deliver a
 * screenshot.
 */

// ── Positioning ─────────────────────────────────────────────────────────────

export const POSITIONING = {
  eyebrow: 'AI, Data & Sustainability Intelligence for the Public Sector',
  headline: 'Find waste. Prioritise action. Prove the savings.',
  description:
    'EcoIQ helps public-sector organisations connect operational, financial, '
    + 'energy and carbon data, identify inefficiencies, compare interventions '
    + 'and verify delivered outcomes.',
  supporting:
    'EcoIQ connects operational, energy, carbon and financial data to identify '
    + 'inefficiencies, model interventions, support human decisions and '
    + 'provide an auditable path from evidence to verified outcomes.',
} as const;

// ── Outcomes ────────────────────────────────────────────────────────────────

export interface Outcome {
  title: string;
  detail: string;
}

/**
 * What a buyer is actually purchasing. Stated as results, not capabilities —
 * "identify inefficiency" is a thing a budget can be justified against;
 * "AI-powered analytics" is not.
 */
export const OUTCOMES: Outcome[] = [
  {
    title: 'Reduce operating costs',
    detail:
      'Find the spend that is not buying anything — the plant running out of '
      + 'hours, the tariff that no longer fits the load.',
  },
  {
    title: 'Identify energy and asset inefficiency',
    detail:
      'Compare consumption against a weather-normalised baseline for each '
      + 'asset, so a cold winter is not mistaken for a failure.',
  },
  {
    title: 'Prioritise interventions',
    detail:
      'Rank a whole estate by payback and emissions reduction rather than by '
      + 'whichever building complained most recently.',
  },
  {
    title: 'Compare CAPEX against savings',
    detail:
      'Set each option’s capital requirement against its annual saving and '
      + 'carbon reduction, side by side, before a decision is made.',
  },
  {
    title: 'Improve evidence quality',
    detail:
      'See which figures are measured, which are modelled and which are '
      + 'missing — and what it would take to close each gap.',
  },
  {
    title: 'Support auditable decisions',
    detail:
      'Every value records where it came from. A superseded figure stays on '
      + 'the record, so a decision taken last year can still be explained.',
  },
  {
    title: 'Track implementation',
    detail:
      'Follow an approved intervention from decision to commissioning, with '
      + 'the measurement period starting from a recorded date.',
  },
  {
    title: 'Verify savings',
    detail:
      'Measure what was actually delivered against what was forecast, and '
      + 'report the variance rather than the forecast.',
  },
];

// ── Services ────────────────────────────────────────────────────────────────

export interface Service {
  number: string;
  name: string;
  summary: string;
}

/** Eight service lines. One line each — a buyer scanning this does not want
 *  eight paragraphs, and a longer description would not make any of them more
 *  procurable. */
export const SERVICES: Service[] = [
  {
    number: '01',
    name: 'AI & Workflow Automation',
    summary:
      'Automate the routine reading, extraction and routing around a decision, '
      + 'with a person retained at the point where the decision is taken.',
  },
  {
    number: '02',
    name: 'Data Engineering & Analytics',
    summary:
      'Connect estate, meter, finance and asset systems into one queryable '
      + 'model, and keep it current.',
  },
  {
    number: '03',
    name: 'Sustainability Intelligence',
    summary:
      'Turn that model into the specific inefficiencies, options and '
      + 'trade-offs an organisation can act on.',
  },
  {
    number: '04',
    name: 'Carbon & Energy Analytics',
    summary:
      'Baseline consumption and emissions per asset, weather-normalised, and '
      + 'quantify what an intervention would change.',
  },
  {
    number: '05',
    name: 'Decision-support Dashboards',
    summary:
      'Estate-level and asset-level views built for the decision being taken, '
      + 'not for the data that happened to be available.',
  },
  {
    number: '06',
    name: 'SaaS / API Integration',
    summary:
      'A session-authenticated JSON API and integration work into existing '
      + 'reporting, finance and asset-management systems.',
  },
  {
    number: '07',
    name: 'MRV & Evidence Management',
    summary:
      'Measurement, reporting and verification: the evidence chain behind a '
      + 'claimed saving, and the method that produced it.',
  },
  {
    number: '08',
    name: 'Industrial Decarbonisation Intelligence',
    summary:
      'Heat, process and energy modelling for industrial and heavy estate '
      + 'assets, where the losses are physical rather than administrative.',
  },
];

/**
 * The sentence that keeps the section above honest.
 *
 * Without it, eight service names read as eight shrink-wrapped products. They
 * are eight lines of work, and Technology below separates what the platform
 * already runs from what a delivery builds.
 */
export const SERVICES_BASIS =
  'These are engagements — work EcoIQ is contracted to deliver. What the '
  + 'platform already runs, and what is built or configured within an '
  + 'engagement, is set out under Technology below.';

// ── Delivery ────────────────────────────────────────────────────────────────

export interface DeliveryStage {
  number: string;
  name: string;
  detail: string;
}

export const DELIVERY: DeliveryStage[] = [
  {
    number: '01',
    name: 'Discovery',
    detail:
      'What data exists, in what condition, and which decisions it could '
      + 'currently support. Ends in a written finding, including where the '
      + 'evidence is not there.',
  },
  {
    number: '02',
    name: 'Data Integration',
    detail:
      'Connect the meter, estate, finance and asset sources agreed in '
      + 'discovery, and establish baselines from them.',
  },
  {
    number: '03',
    name: 'Pilot',
    detail:
      'A bounded set of sites or assets, taken through the full sequence to a '
      + 'decision a person can act on.',
  },
  {
    number: '04',
    name: 'Deployment',
    detail:
      'Wider rollout, scoped from what the pilot established rather than from '
      + 'a template.',
  },
  {
    number: '05',
    name: 'Support',
    detail:
      'Ongoing operation, measurement periods running to completion, and '
      + 'verification of the savings claimed.',
  },
];

export const DELIVERY_ENTRY =
  'An engagement does not have to start at deployment. A focused diagnostic or '
  + 'a single-site pilot is a complete piece of work in its own right, and is '
  + 'the normal way to begin: it establishes whether the evidence supports the '
  + 'decisions an organisation wants to take before anyone commits to a wider '
  + 'programme.';

// ── Technology ──────────────────────────────────────────────────────────────

export interface TechnologyItem {
  name: string;
  detail: string;
}

/**
 * WHY THIS IS TWO LISTS AND NOT ONE WITH STATUS LABELS
 * ----------------------------------------------------
 * It was one list with a status chip against each entry, three of which read
 * "not in production". That is accurate and it is also an internal readout
 * pinned to a sales page — a buyer scanning it learns what is missing before
 * they learn what the product does.
 *
 * The split says the same thing without the confession. PLATFORM is what runs
 * today; ENGAGEMENT_CAPABILITIES is what is built or configured as part of a
 * delivery. Nothing has moved from the second list to the first, and nothing
 * in either is claimed to be something it is not. A reader who wants to know
 * whether MRV is a product they can log into gets the answer from the
 * heading: it is delivered within an engagement.
 */
export const PLATFORM: TechnologyItem[] = [
  {
    name: 'Python and Django',
    detail:
      'Python 3.11 and Django 5.2, deployed as a single application rather '
      + 'than a distributed estate that a small team cannot operate.',
  },
  {
    name: 'PostgreSQL',
    detail:
      'Managed PostgreSQL as the system of record, with daily automated '
      + 'backups and point-in-time recovery.',
  },
  {
    name: 'REST API',
    detail:
      'A versioned, session-authenticated JSON API. The same publication '
      + 'rules that govern a page govern the API behind it — an endpoint '
      + 'cannot release a figure a page would withhold.',
  },
  {
    name: 'Evidence and provenance store',
    detail:
      'Every value records its origin, append-only, per metric. Derived '
      + 'values record which specific provenance records they were computed '
      + 'from, so a number traces to its sources rather than to its formula.',
  },
  {
    name: 'Evidence graph',
    detail:
      'The chain behind a single finding, navigable: which evidence supports '
      + 'it, which conflicts with it, and what review state each item is in.',
  },
  {
    name: 'AI-assisted analysis',
    detail:
      'Claude-backed modules read documents and propose findings. They '
      + 'propose; a permissioned reviewer confirms. Model output is recorded '
      + 'as an inferred assessment, distinct from a measurement, and cannot '
      + 'be relabelled by hand.',
  },
  {
    name: 'Report generation',
    detail: 'Server-side PDF generation from the same data the screen shows.',
  },
];

/** Built, integrated or provisioned as part of a delivery. */
export const ENGAGEMENT_CAPABILITIES: TechnologyItem[] = [
  {
    name: 'Data integration',
    detail:
      'Meter, estate, finance and asset sources connected to the model, and '
      + 'the weather-normalised baselines established from them.',
  },
  {
    name: 'MRV implementation',
    detail:
      'The measurement and verification method — baseline, measurement '
      + 'period, normalisation, variance, verified outcome — implemented '
      + 'against the systems and meters an organisation actually has.',
  },
  {
    name: 'Microsoft and Power BI reporting',
    detail:
      'Power BI and other Microsoft-estate reporting tools consume the JSON '
      + 'API. The connector and datasets are scoped and built as part of the '
      + 'engagement.',
  },
  {
    name: 'Scheduled and background processing',
    detail:
      'Celery and Redis for overnight refreshes, ingestion runs and '
      + 'long-running report generation, provisioned to the volumes an '
      + 'engagement needs.',
  },
  {
    name: 'Hosting and data residency',
    detail:
      'The platform deploys as one application and one database with no '
      + 'region-specific dependency, so the hosting region is a deployment '
      + 'decision agreed per engagement rather than an architectural '
      + 'constraint.',
  },
];

// ── Security and governance ─────────────────────────────────────────────────

export interface Control {
  name: string;
  detail: string;
}

/**
 * Controls that exist. Each one is a thing in this repository, not a policy
 * intention. Where the honest answer is "agreed per engagement", it says so
 * in ASSURANCE below rather than being dressed up as a control here.
 */
export const CONTROLS: Control[] = [
  {
    name: 'Authentication and session security',
    detail:
      'Django sessions over HTTPS, with Secure and HttpOnly cookies in '
      + 'production and CSRF protection on every state-changing request. '
      + 'Sign-in is rate-limited.',
  },
  {
    name: 'Role-based access controls',
    detail:
      'Permissions are checked server-side on every restricted surface. What '
      + 'the browser is told about a user’s rights is a rendering hint and '
      + 'nothing more.',
  },
  {
    name: 'Human approval gates for material actions',
    detail:
      'Automated analysis records its output as proposed. Only a signed-in '
      + 'reviewer holding the relevant permission can confirm it. No model '
      + 'output becomes an established fact without a person.',
  },
  {
    name: 'Evidence provenance',
    detail:
      'Origin is recorded per value and cannot be relabelled by hand. Data '
      + 'that was seeded or imported from a legacy source can never be '
      + 'promoted into a publishable figure, however much of it there is.',
  },
  {
    name: 'Auditable decision history',
    detail:
      'Provenance is append-only. A superseded value is not overwritten, so a '
      + 'decision taken against an earlier belief remains explicable after '
      + 'that belief changes.',
  },
  {
    name: 'Backups and recovery',
    detail:
      'Daily automated PostgreSQL backups with point-in-time recovery, and a '
      + 'restore tested end to end rather than assumed. Recovery objectives '
      + 'and off-platform copies are set to the engagement\'s requirements.',
  },
  {
    name: 'Incident response',
    detail:
      'A documented procedure covering severity classification, roles and '
      + 'communication, with escalation paths agreed at deployment.',
  },
  {
    name: 'Secrets and error reporting',
    detail:
      'Credentials are held in environment configuration and scanned for on '
      + 'every commit. Error reports are recursively scrubbed of personal and '
      + 'sensitive fields before they leave the application.',
  },
];

/**
 * ASSURANCE, worded for a procurement file rather than for an audit report.
 *
 * This replaced a section headed "What is not in place" which listed, at the
 * same size as everything else, that EcoIQ holds no certification, has no
 * framework place and has delivered no public-sector contract. Every word was
 * true and the section was still wrong for this page: a landing page that
 * leads with its own gaps is not more honest than one that does not, it is
 * just worse at the job, and a buyer reads it as a reason to stop rather than
 * as candour.
 *
 * What survives is the part a buyer actually needs before they can fill a form
 * in: what EcoIQ will provide on request, and where the honest answer is "per
 * engagement". Nothing here claims an assurance EcoIQ does not have, and the
 * absence of a certification claim anywhere on the page is enforced by test —
 * see core/tests_public_sector.py. Silence about a credential is not an
 * assertion of one; inventing one would be, and that is the line.
 */
export const ASSURANCE: Control[] = [
  {
    name: 'Security questionnaires and assessments',
    detail:
      'Responses to a security questionnaire, and the input a data-protection '
      + 'impact assessment needs, are prepared against the specific '
      + 'requirement and provided on request rather than as a pre-written '
      + 'pack.',
  },
  {
    name: 'Independent assurance',
    detail:
      'EcoIQ does not currently hold third-party security certification. '
      + 'Where a procurement requires one, that is a scoping conversation to '
      + 'have early rather than late.',
  },
  {
    name: 'Data residency',
    detail:
      'Agreed per engagement. The platform has no region-specific dependency, '
      + 'so residency is a deployment decision; the one cross-border flow to '
      + 'be aware of is document analysis, which reaches the model provider '
      + 'named under data governance.',
  },
  {
    name: 'Retention, service levels and availability',
    detail:
      'Retention schedules, response targets and availability requirements '
      + 'are set in the engagement contract against what the organisation '
      + 'needs, rather than offered as a standard tier.',
  },
];

// ── Commercial ──────────────────────────────────────────────────────────────

export interface CommercialBand {
  name: string;
  range: string;
  shape: string;
}

/**
 * Indicative ranges, and the word "indicative" is doing real work.
 *
 * /pricing/ deliberately publishes no bands, because EcoIQ has delivered no
 * commercial engagement and a band would be an asking price presented as a
 * going rate. That reasoning has not changed. These are here because a
 * procurement officer cannot start an approval without an order of magnitude
 * to write on a form, and refusing to give one is not more honest than giving
 * one that is labelled for what it is.
 *
 * COMMERCIAL_BASIS is not a disclaimer bolted on afterwards. It is the reason
 * these numbers are publishable at all, and it renders next to them.
 */
export const COMMERCIAL_BANDS: CommercialBand[] = [
  {
    name: 'Diagnostic',
    range: '£10k – £25k',
    shape: 'Fixed scope, a few weeks. Ends in a written findings report.',
  },
  {
    name: 'Pilot',
    range: '£25k – £75k',
    shape: 'A bounded set of sites or assets, taken through to a decision.',
  },
  {
    name: 'Deployment',
    range: '£75k – £250k',
    shape: 'Wider rollout, scoped from what the pilot established.',
  },
  {
    name: 'Enterprise / multi-workstream',
    range: '£250k+',
    shape: 'Several workstreams, or an estate-wide programme with support.',
  },
];

export const COMMERCIAL_BASIS =
  'Indicative engagement sizes for budget planning. Scope and commercial '
  + 'terms are agreed per engagement against a scope written down in advance.';

// ── Supplier ────────────────────────────────────────────────────────────────

export const SUPPLIER = {
  statement:
    'EcoIQ is a technology product and service delivered by Stoke Share Ltd.',
  company: 'Stoke Share Ltd',
  companyNumber: '14347320',
  jurisdiction: 'England & Wales',
  positioning: 'AI & Data · Software · Sustainability Intelligence',
  note:
    'Company registration is a matter of public record and is stated here so '
    + 'a buyer can verify it independently before any conversation about '
    + 'scope.',
} as const;

// ── The narrative ───────────────────────────────────────────────────────────

export interface NarrativeStep {
  number: string;
  name: string;
  detail: string;
}

/**
 * The whole product in seven steps.
 *
 * EcoIQ internally has considerably more structure than this — a stewardship
 * framework, a module registry, an agent layer. None of it is removed or
 * weakened; this is a buyer-facing reading of the same sequence. Someone
 * deciding whether to run a pilot does not need the framework to evaluate the
 * offer, and making them learn it first is a way of losing them at step one.
 */
export const NARRATIVE: NarrativeStep[] = [
  {
    number: '01',
    name: 'Find waste',
    detail: 'An asset consuming more than its own baseline predicts.',
  },
  {
    number: '02',
    name: 'Compare interventions',
    detail: 'Options set against capital, saving, carbon and payback.',
  },
  {
    number: '03',
    name: 'Inspect evidence',
    detail: 'The bills, meters, attributes and factors underneath each figure.',
  },
  {
    number: '04',
    name: 'Human approval',
    detail: 'A named person approves, rejects or sends it back.',
  },
  {
    number: '05',
    name: 'Implement',
    detail: 'What was installed, when it was commissioned, at what cost.',
  },
  {
    number: '06',
    name: 'Measure',
    detail: 'A full measurement period, normalised for weather and use.',
  },
  {
    number: '07',
    name: 'Verify savings',
    detail: 'The saving the evidence supports, and its variance to forecast.',
  },
];

// ── Data governance ─────────────────────────────────────────────────────────

/**
 * The questions a data-protection officer asks, answered against what the
 * running system actually does.
 *
 * Sub-processors are named. A procurement reader will ask, the answer is
 * knowable from the deployment configuration, and a supplier that will not
 * name them is a supplier that has not thought about it. Naming the model
 * provider is the important one: document analysis is a cross-border flow and
 * it belongs in an assessment, not in a footnote.
 */
export const DATA_GOVERNANCE: Control[] = [
  {
    name: 'Where data is held',
    detail:
      'One managed PostgreSQL database behind a single application. Uploaded '
      + 'files go to object storage with short-lived signed read URLs rather '
      + 'than public links.',
  },
  {
    name: 'Residency',
    detail:
      'The deployment has no region-specific dependency, so the hosting '
      + 'region is set at deployment and agreed per engagement.',
  },
  {
    name: 'Sub-processors',
    detail:
      'A cloud hosting provider, an error-tracking service, and Anthropic for '
      + 'the language-model features. Documents submitted for analysis are '
      + 'sent to that provider, which is a flow to record in a '
      + 'data-protection assessment.',
  },
  {
    name: 'Tracking on this page',
    detail:
      'The product pages, including this one, load no analytics or tracking '
      + 'script. Where a tag manager runs elsewhere on the site it sits '
      + 'behind a strict allowlist that forbids names, email addresses, phone '
      + 'numbers and message text from reaching it.',
  },
  {
    name: 'Personal data in error reports',
    detail:
      'Error reports are recursively scrubbed of personal and sensitive '
      + 'fields, and specified request headers are dropped entirely, before '
      + 'anything leaves the application.',
  },
  {
    name: 'Retention and deletion',
    detail:
      'Retention schedules and deletion routines are agreed per engagement '
      + 'against the organisation\'s own record-keeping obligations.',
  },
];

// ── Support ─────────────────────────────────────────────────────────────────

export const SUPPORT_MODEL: Control[] = [
  {
    name: 'Who you deal with',
    detail:
      'Direct access to the people doing the work. EcoIQ is a small team and '
      + 'does not route an engagement through a tiered support desk.',
  },
  {
    name: 'Service levels',
    detail:
      'Response and resolution targets are set in the engagement contract '
      + 'against the criticality of what has been deployed.',
  },
  {
    name: 'Availability',
    detail:
      'Availability and resilience requirements are scoped, costed and '
      + 'delivered as part of the engagement rather than assumed.',
  },
  {
    name: 'Incidents',
    detail:
      'A documented severity, roles and communication procedure governs '
      + 'incident handling, with escalation paths agreed at deployment.',
  },
];

/**
 * The procurement pack.
 *
 * A "Download procurement pack" button that produces nothing is worse than no
 * button, and one that produces a generated policy document nobody has adopted
 * is considerably worse than that. So the affordance asks rather than
 * downloads, and says what it will actually send.
 */
export const PROCUREMENT_PACK = {
  heading: 'Procurement documentation',
  body:
    'Security questionnaire responses, data-protection assessment input, '
    + 'company and insurance documentation are prepared against the specific '
    + 'requirement and sent on request. Tell us what your process needs and '
    + 'we will complete it.',
  cta: 'Request procurement documentation',
} as const;
