import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { AppRoutes } from './routes';

/**
 * Smoke gate for the product journeys that matter, end to end.
 *
 * WHY THIS FILE EXISTS
 * --------------------
 * Three defects reached production in this programme and none was caught by the
 * suites that were passing at the time:
 *
 *   - every SPA route answered 404 without its trailing slash;
 *   - a null evidence title crashed the whole investigation page;
 *   - Khalifah gave principle-114 advice on other principles.
 *
 * The unit tests were not wrong. They were narrow: each component was checked
 * against a fixture that happened to be complete, and nothing walked a reader's
 * actual path through several components with realistically incomplete data.
 * That gap is what this closes.
 *
 * WHAT THIS IS, AND HONESTLY IS NOT
 * ---------------------------------
 * jsdom, not a browser. It renders real React through real routes and real
 * fetch payloads, so it catches render crashes, missing state, wrong text and
 * broken DOM order — the classes that actually escaped.
 *
 * It cannot see layout, paint, or computed contrast. The notice-above-verdict
 * requirement is therefore asserted as DOM ORDER, which is the stable
 * invariant; a real browser is still the only thing that proves a pixel. Colour
 * contrast is checked numerically against the tokens elsewhere, not here.
 *
 * No second E2E framework is introduced. The repository's `.mcp.json` declares
 * a Playwright MCP server, but that is an agent tool rather than a CI runner,
 * and adding @playwright/test would mean browser binaries on every CI run for
 * coverage that is mostly reachable here.
 *
 * INCOMPLETE DATA IS THE POINT
 * ----------------------------
 * Fixtures below deliberately omit optional provenance — a null source title, a
 * missing publisher, an unknown publication date, an unclassified authority.
 * The crash that reached production came from exactly that shape, and every
 * existing fixture supplied a title, which is why nothing saw it.
 */

const PRINCIPLE_114 = {
  kpi_id: 114,
  title: 'Consumer Protection & Anti-Manipulation',
  tagline: 'Does it protect informed choice?',
  question: 'Does the organisation actively protect users from manipulation?',
  category: 'social',
  principle_statement: 'Look for dark patterns.',
  metrics: ['dark-pattern prohibition policy', 'consumer complaint rate'],
};

const PRINCIPLE_103 = {
  kpi_id: 103,
  title: 'Time Risk & Transition Urgency',
  tagline: 'Does the pace match what is required?',
  question: 'Does the pace of ESG improvement match transition science?',
  category: 'risk',
  principle_statement: 'Look at pace.',
  metrics: ['emissions reduction pace vs 1.5°C pathway', 'IPCC deadline alignment'],
};

/** Provenance with everything present. */
const FULL_PROVENANCE = {
  has_source_record: true,
  record_reference: 'harvester.Evidence:41',
  title: 'European Commission — non-compliance decision',
  publisher: 'European Commission',
  source_type: 'regulatory_filing',
  url: 'https://ec.europa.eu/decision',
  publication_date: '2026-04-01',
  retrieved_at: '2026-08-27T10:00:00+00:00',
  location: 'Section 4',
  content_hash: 'abc123',
  text_integrity_reference: 'def456',
  authority: { tier: 1, class: 'REGULATOR_OR_STATUTORY_FILING', label: 'Regulator or statutory filing', classified: true },
  ingestion_method: 'harvester_document',
  ingested_at: '2026-08-27T10:00:00+00:00',
  is_demo: false,
};

/**
 * The shape that crashed production: no title, no publisher, no date, no
 * authority tier. Every field here is legitimately absent rather than wrong.
 */
const SPARSE_PROVENANCE = {
  ...FULL_PROVENANCE,
  record_reference: 'harvester.Evidence:99',
  title: null,
  publisher: null,
  source_type: null,
  publication_date: null,
  location: null,
  content_hash: null,
  authority: { tier: null, class: 'UNKNOWN', label: 'Source type not recorded', classified: false },
};

function evidence(over: Record<string, unknown> = {}) {
  return {
    id: 1,
    title: 'European Commission — non-compliance decision',
    relation: 'conflicts',
    legal_status: 'final_regulatory_finding',
    legal_status_strength: 4,
    source_authority: 'European Commission',
    source_url: 'https://ec.europa.eu/decision',
    source_type: 'manual',
    date_collected: '2026-04-01',
    review_tier: 'human_reviewed',
    verification_status: 'verified',
    review_state: 'confirmed',
    counts_toward_assessment: true,
    match_basis: '',
    is_demo: true,
    excerpt: 'The decision text.',
    provenance: FULL_PROVENANCE,
    ...over,
  };
}

function investigation(over: Record<string, unknown> = {}) {
  return {
    company: { slug: 'apple', name: 'Apple', sector: 'other' },
    presentation: {
      is_demonstration: true,
      evidence_is_demo: true,
      is_published: false,
      label: 'DEMONSTRATION — not a published EcoIQ assessment',
      explanation: 'This worked example demonstrates how EcoIQ records evidence.',
    },
    stewardship_principle: PRINCIPLE_114,
    assessment: {
      verdict: 'mixed_material_conflict',
      verdict_label: 'MIXED — MATERIAL CONFLICT',
      confidence: 'VERY_HIGH',
      confidence_reasons: ['A final regulatory finding is present.'],
      rationale: 'Both hold.',
      is_demo: true,
      last_assessed_at: null,
    },
    counts: {
      total: 2, confirmed: 2, supports: 1, conflicts: 1, context: 0,
      excluded_from_assessment: 0, remediation_steps: 1,
    },
    evidence: [
      evidence(),
      evidence({ id: 2, title: null, relation: 'supports',
                 legal_status: 'unclassified', legal_status_strength: 0,
                 provenance: SPARSE_PROVENANCE }),
    ],
    remediation: [{
      position: 1, kind: 'company_action', kind_label: 'Company action',
      summary: 'Changed the flow', detail: '', occurred_on: '2026-05-01',
      verification: 'claimed', verification_label: 'Claimed', evidence_id: null,
    }],
    chain: {
      investigation_started: true,
      evidence_requirements: [],
      evidence: { total: 2, confirmed: 2, awaiting_review: 0, state: 'REVIEWED', detail: '2 confirmed.' },
      standing: { state: 'FINAL_REGULATORY_OR_COURT_FINDING', detail: 'A finding.' },
      finding: { state: 'MIXED', label: 'MIXED', detail: 'Derived.' },
      conflict: { state: 'MATERIAL_CONFLICT', detail: 'Material.' },
      remediation: { state: 'RECORDED', step_count: 1, independently_verified_count: 0, detail: 'One step.' },
      residual_concern: { state: 'REMEDIATION_CLAIMED_NOT_VERIFIED', detail: 'Unchanged.' },
      decision_implication: { state: 'MATERIAL_CONCERN_ON_RECORD', detail: 'On the record.' },
    },
    ...over,
  };
}

/** Routes fetch by URL; this answers each with a realistic payload. */
function mockApi(inv: Record<string, unknown> = investigation()) {
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    const body = url.includes('/kpis/')
      ? inv
      : url.includes('/session/')
        ? { authenticated: false, username: null, is_staff: false }
        : {};
    return { ok: true, status: 200, json: async () => body };
  }));
}

function at(path: string) {
  return render(<MemoryRouter initialEntries={[path]}><AppRoutes /></MemoryRouter>);
}

beforeEach(() => vi.clearAllMocks());

describe('journey · the worked demonstration stays labelled', () => {
  it('reaches the investigation and states it is a demonstration', async () => {
    mockApi();
    at('/companies/apple/kpis/114');
    expect(await screen.findByText(/DEMONSTRATION — not a published EcoIQ assessment/i))
      .toBeInTheDocument();
  });

  it('puts the notice BEFORE the verdict in the document', async () => {
    /**
     * Asserted as DOM order rather than pixel position: order is the stable
     * invariant, and a reader who scrolls straight to the conclusion must meet
     * the notice first. jsdom cannot see layout, so this is the honest form of
     * the assertion.
     */
    mockApi();
    const { container } = at('/companies/apple/kpis/114');
    // By role: "DEMONSTRATION" also appears in the corpus note further down,
    // so a bare text match finds two elements and proves nothing about order.
    await screen.findByRole('note', { name: /demonstration/i });
    const notice = container.querySelector('.kpi-demo')!;
    // The verdict label also appears in the Khalifah panel; take the header's.
    const verdict = container.querySelector('.kpi-header__verdict')!;
    expect(notice.compareDocumentPosition(verdict))
      .toBe(Node.DOCUMENT_POSITION_FOLLOWING);
  });

  it('says a demonstration is not published', async () => {
    mockApi();
    at('/companies/apple/kpis/114');
    const notice = await screen.findByRole('note', { name: /demonstration/i });
    expect(within(notice).getByText(/not a published EcoIQ assessment/i))
      .toBeInTheDocument();
  });

  it('carries no notice when the investigation is not a demonstration', async () => {
    mockApi(investigation({
      presentation: { is_demonstration: false, is_published: false, label: '', explanation: '' },
    }));
    at('/companies/apple/kpis/114');
    await screen.findByText('Consumer Protection & Anti-Manipulation');
    expect(screen.queryByText(/DEMONSTRATION —/i)).not.toBeInTheDocument();
  });
});

describe('journey · incomplete provenance never breaks the route', () => {
  it('renders an investigation whose evidence has no title', async () => {
    /**
     * The exact shape that crashed production: `title: null` reaching
     * `title.split()`. Every pre-existing fixture supplied a title, which is
     * why 6,381 backend and 261 frontend tests all passed while the page was
     * broken.
     */
    mockApi();
    at('/companies/apple/kpis/114');
    expect(await screen.findByText('Consumer Protection & Anti-Manipulation'))
      .toBeInTheDocument();
    expect(screen.queryByText(/Something went wrong/i)).not.toBeInTheDocument();
  });

  it('survives an investigation where EVERY evidence item is sparse', async () => {
    mockApi(investigation({
      evidence: [
        evidence({ id: 1, title: null, provenance: SPARSE_PROVENANCE }),
        evidence({ id: 2, title: null, relation: 'supports', provenance: SPARSE_PROVENANCE }),
      ],
    }));
    at('/companies/apple/kpis/114');
    expect(await screen.findByText('Consumer Protection & Anti-Manipulation'))
      .toBeInTheDocument();
    expect(screen.queryByText(/Something went wrong/i)).not.toBeInTheDocument();
  });

  it('never prints the idempotency key at a reader', async () => {
    mockApi();
    const { container } = at('/companies/apple/kpis/114');
    await screen.findByText('Consumer Protection & Anti-Manipulation');
    expect(container.textContent).not.toMatch(/harvester\.Evidence:/);
  });

  it('opens the drawer for a titled evidence item and deep-links it', async () => {
    mockApi();
    at('/companies/apple/kpis/114');
    await screen.findByText('Consumer Protection & Anti-Manipulation');
    // `shorten()` deliberately labels a node with the half AFTER the dash —
    // the authority is already the sublabel, so leading with it made every node
    // read the same. The accessible name is therefore the distinctive half.
    await userEvent.click(
      screen.getByRole('button', { name: /non-compliance decision/i }));
    expect(await screen.findByRole('complementary', { name: /^Evidence:/ }))
      .toBeInTheDocument();
  });

  it('opens a drawer for an UNTITLED evidence item without crashing', async () => {
    mockApi();
    at('/companies/apple/kpis/114?evidence=2');
    await screen.findByText('Consumer Protection & Anti-Manipulation');
    const drawer = await screen.findByRole('complementary', { name: /^Evidence:/ });
    expect(within(drawer).getByText(/Untitled source/i)).toBeInTheDocument();
  });

  it('restores the selected evidence item from the URL', async () => {
    mockApi();
    at('/companies/apple/kpis/114?evidence=1');
    expect(await screen.findByRole('complementary', {
      name: 'Evidence: European Commission — non-compliance decision',
    })).toBeInTheDocument();
  });

  it('ignores an evidence id the investigation does not contain', async () => {
    mockApi();
    at('/companies/apple/kpis/114?evidence=99999');
    expect(await screen.findByText(/Select any evidence item/i)).toBeInTheDocument();
  });
});

describe('journey · Khalifah speaks about this principle, and says it is a demo', () => {
  it('states the demonstration context before explaining anything', async () => {
    mockApi();
    at('/companies/apple/kpis/114');
    expect(await screen.findByText(/Explaining a worked example/i)).toBeInTheDocument();
  });

  it('uses THIS principle\'s indicators, not principle 114\'s', async () => {
    /**
     * The regression: these lists were written for #114 and rendered for every
     * principle, so Walmart against "Time Risk & Transition Urgency" was told
     * to keep security warnings proportionate.
     */
    mockApi(investigation({
      stewardship_principle: PRINCIPLE_103,
      presentation: { is_demonstration: false, is_published: false, label: '', explanation: '' },
    }));
    at('/companies/walmart/kpis/103');
    await screen.findByText('Time Risk & Transition Urgency');
    await userEvent.click(screen.getByRole('button', { name: /strengthen/i }));
    expect(await screen.findByText('emissions reduction pace vs 1.5°C pathway'))
      .toBeInTheDocument();
  });

  it('carries none of the principle-114 language on another principle', async () => {
    mockApi(investigation({
      stewardship_principle: PRINCIPLE_103,
      presentation: { is_demonstration: false, is_published: false, label: '', explanation: '' },
    }));
    const { container } = at('/companies/walmart/kpis/103');
    await screen.findByText('Time Risk & Transition Urgency');
    await userEvent.click(screen.getByRole('button', { name: /strengthen/i }));
    for (const leak of [/security warning/i, /switching.friction/i, /default path/i]) {
      expect(container.textContent).not.toMatch(leak);
    }
  });
});

describe('journey · proposed evidence never reads as confirmed', () => {
  it('shows awaiting-review evidence as counting toward nothing', async () => {
    mockApi(investigation({
      presentation: { is_demonstration: false, is_published: false, label: '', explanation: '' },
      assessment: {
        verdict: 'insufficient_evidence', verdict_label: 'INSUFFICIENT EVIDENCE',
        confidence: 'INSUFFICIENT_EVIDENCE',
        confidence_reasons: ['No confirmed evidence is linked to this principle.'],
        rationale: '', is_demo: false, last_assessed_at: null,
      },
      counts: {
        total: 2, confirmed: 0, supports: 0, conflicts: 0, context: 0,
        excluded_from_assessment: 2, remediation_steps: 0,
      },
      evidence: [
        evidence({ id: 1, review_state: 'proposed', counts_toward_assessment: false, is_demo: false }),
        evidence({ id: 2, review_state: 'proposed', counts_toward_assessment: false, is_demo: false }),
      ],
    }));
    at('/companies/walmart/kpis/114');
    // The empty state owns this heading; the verdict label says the same words
    // elsewhere, so scope to the section rather than matching loose text.
    expect(await screen.findByRole('heading', { name: /Insufficient evidence/i }))
      .toBeInTheDocument();
    expect(screen.getByText(/not in a confirmed review state/i)).toBeInTheDocument();
  });
});
