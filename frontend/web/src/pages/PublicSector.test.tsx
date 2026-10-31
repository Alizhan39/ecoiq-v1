import { describe, expect, it } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import PublicSector from './PublicSector';

function renderPage() {
  return render(
    <MemoryRouter>
      <PublicSector />
    </MemoryRouter>,
  );
}

function pageText(): string {
  const { container } = renderPage();
  return container.textContent ?? '';
}

/**
 * The acceptance test for this page is a person: can a procurement officer
 * answer what it does, what it fixes, what they can buy, how a recommendation
 * is reached and evidenced, who decides, how the saving is proved, who the
 * supplier is, what it costs, and what to do next — in about a minute, without
 * leaving the page?
 *
 * These assert those answers are here, that the demonstration is embedded
 * rather than linked, and that nothing on the page claims a credential,
 * client or capability EcoIQ does not have.
 */

describe('the sixty-second read', () => {
  it('says what EcoIQ does, in the headline', () => {
    renderPage();

    expect(screen.getByRole('heading', { level: 1 }))
      .toHaveTextContent('Find waste. Prioritise action. Prove the savings.');
  });

  it('names the sector in the eyebrow', () => {
    renderPage();

    expect(screen.getByText(/AI, Data & Sustainability Intelligence for the Public Sector/i))
      .toBeInTheDocument();
  });

  it('states the outcomes a budget is justified against', () => {
    renderPage();
    // Scoped: "Verify savings" is deliberately both an outcome and the last
    // step of the story below — the two agreeing is the point, and an
    // unscoped query cannot tell them apart.
    const outcomes = screen.getByRole('region', { name: 'What it delivers' });

    for (const outcome of ['Reduce operating costs', 'Prioritise interventions',
                           'Verify savings', 'Support auditable decisions']) {
      expect(within(outcomes).getByRole('heading', { name: outcome }))
        .toBeInTheDocument();
    }
  });

  it('lists the eight service lines', () => {
    renderPage();

    for (const service of [
      'AI & Workflow Automation', 'Data Engineering & Analytics',
      'Sustainability Intelligence', 'Carbon & Energy Analytics',
      'Decision-support Dashboards', 'SaaS / API Integration',
      'MRV & Evidence Management', 'Industrial Decarbonisation Intelligence',
    ]) {
      expect(screen.getByRole('heading', { name: service })).toBeInTheDocument();
    }
  });

  it('shows the delivery model as a sequence', () => {
    renderPage();
    const delivery = screen.getByRole('region', { name: 'Delivery model' });

    for (const stage of ['Discovery', 'Data Integration', 'Pilot',
                         'Deployment', 'Support']) {
      expect(within(delivery).getByRole('heading', { name: stage }))
        .toBeInTheDocument();
    }
  });

  it('gives a price a buyer can put on a form, labelled indicative', () => {
    renderPage();

    expect(screen.getByRole('heading', { name: /indicative engagement sizes/i }))
      .toBeInTheDocument();
    for (const band of ['£10k – £25k', '£25k – £75k', '£75k – £250k', '£250k+']) {
      expect(screen.getByText(band)).toBeInTheDocument();
    }
    expect(screen.getByText(/Scope and commercial terms are agreed per engagement/i))
      .toBeInTheDocument();
  });

  it('names the UK supplier and its company number', () => {
    renderPage();
    const supplier = screen.getByRole('region', {
      name: 'Supplier and procurement information',
    });

    expect(within(supplier).getAllByText(/Stoke Share Ltd/).length)
      .toBeGreaterThanOrEqual(1);
    expect(within(supplier).getByText('14347320')).toBeInTheDocument();
    expect(within(supplier).getByText('England & Wales')).toBeInTheDocument();
  });

  it('ends at a next action that reaches the real enquiry funnel', () => {
    renderPage();
    const cta = screen.getByRole('region', { name: 'Request a pilot' });

    expect(within(cta).getByRole('link', { name: 'Request a pilot' }))
      .toHaveAttribute(
        'href', '/request-access/enterprise/?engagement=government_sovereign');
  });
});

describe('everything is on this one page', () => {
  it('embeds the borough demonstration rather than linking to it', () => {
    renderPage();

    expect(screen.getByRole('heading', {
      level: 2, name: 'London Borough Sustainability Command Centre',
    })).toBeInTheDocument();
  });

  it('carries the asset drill-down, evidence, approval and MRV inline', () => {
    renderPage();

    expect(screen.getByRole('table', { name: /flagged assets/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 3, name: 'Leisure Centre' }))
      .toBeInTheDocument();
    expect(screen.getByRole('region', { name: /evidence behind the recommendation/i }))
      .toBeInTheDocument();
    expect(screen.getByRole('region', { name: /human approval required/i }))
      .toBeInTheDocument();
    expect(screen.getByRole('region', { name: /measurement and verification/i }))
      .toBeInTheDocument();
  });

  it('carries the procurement detail inline', () => {
    renderPage();
    const supplier = screen.getByRole('region', {
      name: 'Supplier and procurement information',
    });

    expect(within(supplier).getByRole('heading', { name: /support/i }))
      .toBeInTheDocument();
    expect(within(supplier).getByRole('heading', { name: /assurance and documentation/i }))
      .toBeInTheDocument();
  });

  it('links nowhere else in the public-sector surface', () => {
    // The extra routes are gone. A link to one would 404, and an in-page
    // anchor is what replaced them.
    const { container } = renderPage();
    const hrefs = Array.from(container.querySelectorAll('a[href]'))
      .map((a) => a.getAttribute('href')!);

    for (const href of hrefs) {
      expect(href).not.toMatch(/^\/public-sector\/./);
      expect(href).not.toBe('/procurement/');
    }
    expect(hrefs).toContain('#borough-demo');
    expect(hrefs).toContain('#procurement');
  });

  it('anchors those two jump targets at elements that exist', () => {
    const { container } = renderPage();

    for (const id of ['borough-demo', 'procurement']) {
      expect(container.querySelector(`#${id}`)).not.toBeNull();
    }
  });

  it('tells the core story in the buyer’s own sequence', () => {
    renderPage();
    const story = screen.getByRole('region', {
      name: /the sequence this demonstration walks through/i,
    });

    expect(
      within(story).getAllByRole('heading', { level: 4 })
        .map((node) => node.textContent),
    ).toEqual([
      'Find waste', 'Compare interventions', 'Inspect evidence',
      'Human approval', 'Implement', 'Measure', 'Verify savings',
    ]);
  });
});

describe('claims that must never appear', () => {
  it('claims no certification, framework place or approval', () => {
    const text = pageText();

    for (const pattern of [
      /\bISO 27001\b/i, /\bCyber Essentials\b/i, /\bSOC 2\b/i, /\bG-Cloud\b/i,
      /\bCCS framework\b/i, /\bgovernment approved\b/i,
      /\bframework supplier\b/i, /\bapproved supplier\b/i,
      /\bfully compliant\b/i, /\bcertified\b/i, /\baccredited\b/i,
    ]) {
      expect(text).not.toMatch(pattern);
    }
  });

  it('claims no client, case study or delivered saving', () => {
    const text = pageText();

    for (const pattern of [
      /\bour clients\b/i, /\bour customers\b/i, /\btrusted by\b/i,
      /\bcase study\b/i, /\bproven savings\b/i, /\bdelivered savings of\b/i,
    ]) {
      expect(text).not.toMatch(pattern);
    }
  });

  it('does not claim UK data residency', () => {
    const text = pageText();

    expect(text).not.toMatch(/UK data residency/i);
    expect(text).not.toMatch(/data (is )?held in the UK/i);
    expect(text).not.toMatch(/UK[- ]hosted/i);
    // What it says instead: residency is a deployment decision, which is what
    // the architecture actually supports.
    expect(text).toMatch(/no region-specific dependenc/i);
  });

  it('does not claim a native Microsoft or Power BI integration', () => {
    const text = pageText();

    expect(text).not.toMatch(/native (Power BI|Microsoft) integration/i);
    expect(text).toMatch(/scoped and built as part of the engagement/i);
  });

  it('does not present indicative sizes as validated pricing', () => {
    const text = pageText();

    expect(text).toMatch(/Indicative engagement sizes for budget planning/i);
    expect(text).not.toMatch(/market rate/i);
    expect(text).not.toMatch(/typical(ly)? costs?\b/i);
  });

  it('names the model sub-processor rather than omitting it', () => {
    // Document analysis is a cross-border flow and a DPO will ask.
    expect(pageText()).toMatch(/Anthropic/);
  });
});

describe('it reads as a supplier page, not an internal audit', () => {
  it('has no section headed with what is missing', () => {
    renderPage();

    expect(screen.queryByRole('heading', { name: /what is not in place/i }))
      .toBeNull();
    expect(screen.queryByRole('heading', { name: /limitations/i })).toBeNull();
  });

  it('does not lead with absences', () => {
    const text = pageText();

    for (const pattern of [
      /\bno reference customer\b/i,
      /\bhas not yet delivered a public-sector contract\b/i,
      /\bnot provisioned\b/i,
      /\bno standard published SLA\b/i,
      /\bno published .{0,30}retention schedule\b/i,
      /\bno failover\b/i,
      /\bno staging environment\b/i,
      /\bdepends on a person noticing\b/i,
      /\bthere is no self-serve\b/i,
    ]) {
      expect(text).not.toMatch(pattern);
    }
  });

  it('still answers the assurance question where a buyer looks for it', () => {
    // Not advertised, not hidden: one factual line, in the procurement
    // section, worded for a procurement file.
    renderPage();
    const supplier = screen.getByRole('region', {
      name: 'Supplier and procurement information',
    });

    expect(within(supplier).getByText(
      /does not currently hold third-party security certification/i))
      .toBeInTheDocument();
  });

  it('offers procurement documentation instead of a broken download', () => {
    const text = pageText();

    expect(text).toMatch(/sent on request/i);
    expect(screen.getAllByRole('link', {
      name: /request procurement documentation/i,
    }).length).toBeGreaterThanOrEqual(1);
  });
});

describe('accessibility', () => {
  it('gives every section a heading it is labelled by', () => {
    const { container } = renderPage();

    for (const section of Array.from(container.querySelectorAll('section'))) {
      const id = section.getAttribute('aria-labelledby');
      expect(id).toBeTruthy();
      expect(container.querySelector(`#${CSS.escape(id!)}`)).not.toBeNull();
    }
  });

  it('has exactly one h1', () => {
    const { container } = renderPage();

    expect(container.querySelectorAll('h1')).toHaveLength(1);
  });

  it('starts at h1 and skips no level below it', () => {
    const { container } = renderPage();
    const levels = Array.from(container.querySelectorAll('h1,h2,h3,h4,h5'))
      .map((node) => Number(node.tagName[1]));

    expect(levels[0]).toBe(1);
    for (let i = 1; i < levels.length; i += 1) {
      expect(levels[i]! - levels[i - 1]!).toBeLessThanOrEqual(1);
    }
  });

  it('keeps every wide table inside its own scroll container', () => {
    const { container } = renderPage();

    for (const table of Array.from(container.querySelectorAll('table'))) {
      expect(table.closest('.psassets__scroll')).not.toBeNull();
    }
  });
});
