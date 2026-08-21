import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import TrustCenter from './TrustCenter';

describe('claims that must never appear', () => {
  it('claims no certification EcoIQ does not hold', () => {
    const { container } = render(<TrustCenter />);
    const text = container.textContent ?? '';

    // Scoped to AFFIRMATIVE phrasings. A blanket substring ban would also
    // reject the denials ("not ISO certified"), which are the whole point of
    // the section — and a test that forbids the honest sentence would push
    // the page toward saying nothing at all.
    expect(text).not.toMatch(/\bis SOC 2 certified/i);
    expect(text).not.toMatch(/\bwe are (SOC|ISO|GDPR)/i);
    expect(text).not.toMatch(/\bcertified to ISO/i);
    expect(text).not.toMatch(/\bfully compliant\b/i);

    // And the denials must be present.
    expect(text).toMatch(/not SOC 2 audited/i);
    expect(text).toMatch(/no such thing as GDPR certification/i);
  });

  it('states plainly that there are no certifications', () => {
    render(<TrustCenter />);

    expect(screen.getByText(/not SOC 2 audited/i)).toBeInTheDocument();
  });

  it('does not claim a production AI agent', () => {
    render(<TrustCenter />);

    expect(screen.getByText(/No AI module is claimed as production/i))
      .toBeInTheDocument();
  });
});

describe('the page states what is missing', () => {
  it('has a section for what is not in place', () => {
    render(<TrustCenter />);

    // A trust page that lists only strengths is not a trust page.
    expect(screen.getByRole('heading', { name: /what is not in place/i }))
      .toBeInTheDocument();
  });

  it('admits evaluation has not been done', () => {
    render(<TrustCenter />);

    expect(screen.getByText(/No formal AI evaluation yet/i)).toBeInTheDocument();
  });

  it('admits contradiction detection is absent', () => {
    render(<TrustCenter />);

    expect(screen.getByText(/Contradiction detection is not implemented/i))
      .toBeInTheDocument();
  });
});

describe('the core commitments', () => {
  it('explains that unknown is never a number', () => {
    render(<TrustCenter />);

    expect(screen.getByText(/Unknown is never a number/i)).toBeInTheDocument();
  });

  it('explains that coverage and confidence are separate', () => {
    render(<TrustCenter />);

    expect(screen.getByText(/Coverage and confidence are separate/i))
      .toBeInTheDocument();
  });

  it('explains that AI may propose but not confirm', () => {
    render(<TrustCenter />);

    expect(screen.getByText(/AI may propose\. It may not confirm\./i))
      .toBeInTheDocument();
  });

  it('states that seeded data can never publish', () => {
    render(<TrustCenter />);

    expect(screen.getByText(/never become publishable/i)).toBeInTheDocument();
  });
});
