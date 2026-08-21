/**
 * The rule carried forward from the #270 league-chart breach.
 *
 * That leak happened because the SERVER handed the template numbers the UI
 * intended to hide, and one surface forgot to hide them. Containment that
 * depends on every renderer remembering is not containment.
 *
 * So the rule is: React must never RECEIVE an unpublished numerical score.
 * These tests assert both halves — that the client does not render one, and
 * that a payload carrying one would be a backend contract violation rather
 * than something the client is expected to conceal.
 */
import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Assessment } from './Assessment';
import type { CompanyDetail } from '@/types/evidence';

const WITHHELD: CompanyDetail = {
  slug: 'withheld-co',
  name: 'Withheld Co',
  sector: 'other',
  country: 'UK',
  city: '',
  website: '',
  logo_url: null,
  description: '',
  is_public: true,
  verified: false,
  ecoiq_score: null,
  score_status: 'INSUFFICIENT_EVIDENCE',
  evidence_coverage: 0,
  confidence: 'INSUFFICIENT_EVIDENCE',
  evidence_note: 'Not enough verified evidence to publish an assessment.',
  harm_signals: [],
};

const PUBLISHED: CompanyDetail = {
  ...WITHHELD,
  slug: 'published-co',
  name: 'Published Co',
  ecoiq_score: 76.4,
  score_status: 'PUBLISHED',
  evidence_coverage: 100,
  confidence: 'HIGH',
  evidence_note: '',
};

describe('a withheld score', () => {
  it('renders no number', () => {
    const { container } = render(<Assessment company={WITHHELD} />);

    // "Insufficient evidence" appears twice — as the confidence LABEL and as
    // the withheld-score state — so assert on the score element itself.
    expect(container.querySelector('.score--withheld')).toBeTruthy();
    expect(container.querySelector('.score__value')).toBeNull();
    expect(screen.queryByText(/\/100 EcoIQ score/)).toBeNull();
  });

  it('explains itself in the backend’s own words', () => {
    render(<Assessment company={WITHHELD} />);

    expect(screen.getByText(WITHHELD.evidence_note)).toBeInTheDocument();
  });

  it('does not substitute a zero', () => {
    const { container } = render(<Assessment company={WITHHELD} />);

    expect(container.textContent).not.toMatch(/\b0\.0\b/);
  });

  it('still shows coverage and confidence', () => {
    const { container } = render(<Assessment company={WITHHELD} />);

    // Withholding the SCORE is not withholding the evidence state — the
    // reader needs to know how far from publishable this is.
    const values = Array.from(container.querySelectorAll('.evidence__item dd'))
      .map((node) => node.textContent);

    expect(values).toContain('0%');
    expect(values).toContain('Insufficient evidence');
  });

  it('says what would change the answer', () => {
    render(<Assessment company={WITHHELD} />);

    expect(screen.getByText(/What would change this/i)).toBeInTheDocument();
  });
});

describe('the API must not send what the UI would hide', () => {
  it('a withheld payload carries a null score, not a hidden number', () => {
    // If this ever fails, the defect is in the SERIALIZER, not the component.
    // The client is not the containment boundary and must not become one.
    expect(WITHHELD.ecoiq_score).toBeNull();
    expect(WITHHELD.score_status).not.toBe('PUBLISHED');
  });

  it('a score present with a non-published status is a contract violation', () => {
    const violating = { ...WITHHELD, ecoiq_score: 71.4 };

    // The component still refuses to render it — defence in depth — but the
    // real fix for such a payload is server-side.
    const { container } = render(<Assessment company={violating} />);

    expect(screen.queryByText('71.4')).toBeNull();
    expect(container.querySelector('.score--withheld')).toBeTruthy();
  });

  it('never derives a score from coverage', () => {
    const { container } = render(
      <Assessment company={{ ...WITHHELD, evidence_coverage: 62 }} />,
    );

    // 62% coverage is not a score of 62.
    expect(container.textContent).toContain('62%');
    expect(container.textContent).not.toMatch(/62\.0\s*\/100/);
  });
});

describe('a published score', () => {
  it('renders the real number', () => {
    render(<Assessment company={PUBLISHED} />);

    expect(screen.getByText('76.4')).toBeInTheDocument();
  });

  it('renders a genuine zero as zero', () => {
    render(<Assessment company={{ ...PUBLISHED, ecoiq_score: 0 }} />);

    // A company assessed at zero is a finding, not a missing value.
    expect(screen.getByText('0.0')).toBeInTheDocument();
    expect(screen.queryByText(/Insufficient evidence/i)).toBeNull();
  });

  it('does not show the "what would change this" section', () => {
    render(<Assessment company={PUBLISHED} />);

    expect(screen.queryByText(/What would change this/i)).toBeNull();
  });
});

describe('harm signals', () => {
  const signal = (status: string) => ({
    id: 'x', label: 'Controversy Risk', status, penalty: 0, detail: 'detail',
  });

  it('never renders an unassessed signal as clear', () => {
    render(
      <Assessment
        company={{ ...WITHHELD, harm_signals: [signal('insufficient_evidence')] }}
      />,
    );

    expect(screen.getByText('Not assessed')).toBeInTheDocument();
    expect(screen.queryByText('Clear')).toBeNull();
  });

  it('renders a genuinely clear signal as clear', () => {
    render(
      <Assessment company={{ ...WITHHELD, harm_signals: [signal('clear')] }} />,
    );

    expect(screen.getByText('Clear')).toBeInTheDocument();
  });
});
