import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Pricing from './Pricing';

function show() {
  return render(<MemoryRouter><Pricing /></MemoryRouter>);
}

describe('pricing is enquiry-led, not productised', () => {
  it('publishes no price figure', () => {
    const { container } = show();

    // The page this replaces published four bands — £15,000 to £400,000 — for
    // engagements that have never been sold.
    expect(container.textContent).not.toMatch(/[£$€]\s?\d/);
  });

  it('invents no subscription tier', () => {
    show();
    for (const tier of [/per month/i, /\/mo\b/i, /billed annually/i,
      /Starter/i, /Premium/i]) {
      expect(screen.queryByText(tier)).not.toBeInTheDocument();
    }
  });

  it('says why there are no figures', () => {
    show();
    expect(screen.getByText(/no published price bands/i)).toBeInTheDocument();
  });

  it('routes to the real enterprise enquiry form', () => {
    show();
    expect(screen.getByRole('link', { name: /Start an enquiry/i }))
      .toHaveAttribute('href', '/request-access/enterprise/');
  });

  it('keeps every engagement key the enquiry form understands', () => {
    // The form pre-selects the engagement type from this query parameter.
    // Dropping one would quietly route that segment into a generic enquiry.
    const { container } = show();
    for (const key of ['enterprise_diagnostic', 'pilot_90day',
      'enterprise_deployment', 'annual_licence', 'government_sovereign',
      'founding_partner']) {
      expect(container.querySelector(
        `a[href="/request-access/enterprise/?engagement=${key}"]`)).not.toBeNull();
    }
  });

  it('does not count its own cards wrong', () => {
    // The heading said "Four ways" while six cards rendered beneath it.
    const { container } = show();
    const cards = container.querySelectorAll('.grid > .card').length;
    expect(container.textContent).not.toMatch(/\b(Four|Five|Six|Seven) ways\b/);
    expect(cards).toBe(6);
  });

  it('keeps the real engagement shapes', () => {
    show();
    for (const name of ['Diagnostic', 'Pilot', 'Deployment', 'Programme',
      'Government and sovereign', 'Founding partner']) {
      expect(screen.getByRole('heading', { name })).toBeInTheDocument();
    }
  });

  it('never shows a buy-now control', () => {
    const { container } = show();
    expect(container.textContent).not.toMatch(/buy now/i);
  });

  it('promises no unbuilt capability', () => {
    const { container } = show();
    // The replaced page itemised SSO, workflow automation and overnight
    // monitoring as included. None of those is implemented.
    for (const claim of [/\bSSO\b/, /workflow automation/i,
      /overnight monitoring/i]) {
      expect(container.textContent).not.toMatch(claim);
    }
  });
});
