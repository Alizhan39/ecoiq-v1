import { describe, expect, it } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BoroughCommandCentre } from './BoroughCommandCentre';

function renderDemo() {
  return render(<BoroughCommandCentre headingId="demo" />);
}

/**
 * The demonstration, tested as the section it now is.
 *
 * These assertions came across intact from the page suite that covered it when
 * it was /public-sector/borough-demo/. What it renders did not change when it
 * stopped being a route; only its heading levels did, and the tests that
 * assert on level rather than on text say so explicitly.
 */

describe('demonstration labelling', () => {
  it('says it is a fictitious dataset, above the figures', () => {
    renderDemo();
    const notices = screen.getAllByRole('note', { name: /demonstration data/i });

    expect(notices.length).toBeGreaterThanOrEqual(1);
    expect(notices[0]).toHaveTextContent(/fictitious demonstration dataset/i);
  });

  it('repeats the notice at the end of the section', () => {
    // A reader who scrolled the whole demonstration must not arrive at the
    // sections below it having forgotten what the numbers were.
    renderDemo();

    expect(screen.getAllByRole('note', { name: /demonstration data/i }).length)
      .toBeGreaterThanOrEqual(2);
  });

  it('denies that any of it is a client outcome', () => {
    const { container } = renderDemo();
    const text = container.textContent ?? '';

    expect(text).toMatch(/no real organisation, asset, saving or client outcome/i);
    expect(text).not.toMatch(/\bour client\b/i);
    expect(text).not.toMatch(/\bcase study\b/i);
  });
});

describe('the headline figures', () => {
  it('shows buildings, spend, emissions and the saving opportunity', () => {
    renderDemo();

    expect(screen.getByText('127')).toBeInTheDocument();
    expect(screen.getByText('£8.4m')).toBeInTheDocument();
    expect(screen.getByText(/14,820/)).toBeInTheDocument();
    expect(screen.getByText('£740,000')).toBeInTheDocument();
  });

  it('says how many assets require attention', () => {
    renderDemo();

    expect(screen.getByText('17 assets require attention')).toBeInTheDocument();
  });

  it('states that the headline is the sum of the rows', () => {
    renderDemo();

    expect(screen.getByText(/is the sum of the 17 assets listed below/i))
      .toBeInTheDocument();
  });
});

describe('the asset table', () => {
  it('lists every flagged asset with its payback', () => {
    renderDemo();
    const table = screen.getByRole('table', { name: /flagged assets/i });

    // 17 assets + a header row + a totals row.
    expect(within(table).getAllByRole('row')).toHaveLength(19);
  });

  it('opens on the priority asset so the flow is visible on arrival', () => {
    renderDemo();

    expect(screen.getByRole('heading', { level: 3, name: 'Leisure Centre' }))
      .toBeInTheDocument();
    expect(screen.getByText('Priority 01')).toBeInTheDocument();
  });

  it('lets a reader drill into another asset', async () => {
    renderDemo();
    const table = screen.getByRole('table', { name: /flagged assets/i });

    await userEvent.click(
      within(table).getByRole('button', { name: 'Council Office' }));

    expect(screen.getByRole('heading', { level: 3, name: 'Council Office' }))
      .toBeInTheDocument();
  });

  it('marks the selected asset for assistive technology', async () => {
    renderDemo();
    const table = screen.getByRole('table', { name: /flagged assets/i });

    await userEvent.click(within(table).getByRole('button', { name: 'School A' }));

    expect(within(table).getByRole('button', { name: 'School A' }))
      .toHaveAttribute('aria-current', 'true');
  });

  it('says where the deeper analysis stops rather than inventing it', async () => {
    renderDemo();
    const table = screen.getByRole('table', { name: /flagged assets/i });

    await userEvent.click(within(table).getByRole('button', { name: 'Library A' }));

    expect(screen.getByText(/has not been invented for this asset/i))
      .toBeInTheDocument();
  });
});

describe('the priority drill-down', () => {
  it('reports the anomaly against a baseline, not against nothing', () => {
    renderDemo();
    const anomaly = screen.getByRole('region', { name: /energy anomaly detected/i });

    expect(within(anomaly).getByText(/\+31\.0% versus expected baseline/))
      .toBeInTheDocument();
    expect(within(anomaly).getByText('£96,000')).toBeInTheDocument();
    expect(within(anomaly).getByText(/weather-normalised baseline/i))
      .toBeInTheDocument();
  });

  it('lists the candidate causes as candidates', () => {
    renderDemo();
    const anomaly = screen.getByRole('region', { name: /energy anomaly detected/i });

    for (const cause of ['Boiler inefficiency', 'Poor controls',
                         'Heating schedule mismatch', 'Building fabric losses']) {
      expect(within(anomaly).getByText(cause)).toBeInTheDocument();
    }
    expect(within(anomaly).getByText(/Candidates, not findings/i))
      .toBeInTheDocument();
  });

  it('compares three interventions on capital, saving, carbon and payback', () => {
    renderDemo();
    const table = screen.getByRole('table', { name: /interventions compared/i });

    expect(within(table).getAllByRole('row')).toHaveLength(4);
    expect(within(table).getByText('0.7 years')).toBeInTheDocument();
    expect(within(table).getByText('3.5 years')).toBeInTheDocument();
  });

  it('presents the sequence as decision support, not as an action', () => {
    renderDemo();

    expect(screen.getByText(/AI-assisted decision support/i)).toBeInTheDocument();
    expect(screen.getByText(/does not procure, commit capital/i))
      .toBeInTheDocument();
  });
});

describe('evidence', () => {
  it('shows source, date, confidence, methodology and status', () => {
    renderDemo();
    const table = screen.getByRole('table', { name: /evidence items/i });

    for (const column of ['Source', 'Date', 'Confidence', 'Methodology',
                          'Status']) {
      expect(within(table).getByRole('columnheader', { name: column }))
        .toBeInTheDocument();
    }
  });

  it('lists the evidence types the recommendation rests on', () => {
    renderDemo();
    const table = screen.getByRole('table', { name: /evidence items/i });

    for (const type of ['Energy bills', 'Meter readings', 'Building attributes',
                        'Weather-normalised baseline', 'Tariff data',
                        'Maintenance history', 'Emission factors']) {
      expect(within(table).getByRole('rowheader', { name: type }))
        .toBeInTheDocument();
    }
  });

  it('makes the traceability claim, and shows a weak link', () => {
    renderDemo();

    expect(screen.getByText(/Recommendation backed by traceable evidence/i))
      .toBeInTheDocument();
    expect(screen.getByText('Outstanding')).toBeInTheDocument();
  });
});

describe('the human approval gate', () => {
  it('holds the recommendation pending a person', () => {
    renderDemo();

    expect(screen.getByText('Needs human approval')).toBeInTheDocument();
  });

  it('offers approve, reject and request further analysis', () => {
    renderDemo();
    const gate = screen.getByRole('region', { name: /human approval required/i });

    for (const label of ['Approve', 'Reject', 'Request further analysis']) {
      expect(within(gate).getByRole('button', { name: label }))
        .toBeInTheDocument();
    }
  });

  it('describes the consequence in the conditional and records nothing', async () => {
    renderDemo();
    const gate = screen.getByRole('region', { name: /human approval required/i });

    await userEvent.click(within(gate).getByRole('button', { name: 'Approve' }));

    expect(within(gate).getByText(/In a live deployment, approve would:/i))
      .toBeInTheDocument();
    expect(within(gate).getByText(/Nothing was recorded/i)).toBeInTheDocument();
  });

  it('says nothing is submitted before anything is pressed', () => {
    renderDemo();

    expect(screen.getByText(/Nothing is submitted/i)).toBeInTheDocument();
  });
});

describe('measurement and verification', () => {
  it('runs the full loop, named', () => {
    renderDemo();
    const mrv = screen.getByRole('region', { name: /measurement and verification/i });

    for (const stage of ['Baseline', 'Intervention', 'Measurement period',
                         'Normalisation', 'Actual saving', 'Variance',
                         'Verified outcome']) {
      expect(within(mrv).getByRole('heading', { name: stage }))
        .toBeInTheDocument();
    }
  });

  it('reports the verified saving, the forecast and the variance', () => {
    renderDemo();
    const mrv = screen.getByRole('region', { name: /measurement and verification/i });

    expect(within(mrv).getByText('£76,420')).toBeInTheDocument();
    expect(within(mrv).getByText('£79,000')).toBeInTheDocument();
    expect(within(mrv).getByText('−3.3%')).toBeInTheDocument();
    expect(within(mrv).getByText('VERIFIED')).toBeInTheDocument();
  });

  it('does not present a verified outcome as a validated forecast', () => {
    renderDemo();

    expect(screen.getByText(/not that the forecast was right/i))
      .toBeInTheDocument();
  });

  it('states no variance figure in prose, only the computed one', () => {
    // The caveat used to read "here it was 3.3% optimistic" — the variance,
    // restated by hand next to the figure economics.ts computes.
    renderDemo();
    const mrv = screen.getByRole('region', { name: /measurement and verification/i });

    expect(within(mrv).getAllByText('−3.3%')).toHaveLength(1);
  });
});

describe('the sequence it walks through', () => {
  it('names the seven steps of the buyer story', () => {
    renderDemo();

    for (const step of ['Find waste', 'Compare interventions',
                        'Inspect evidence', 'Human approval', 'Implement',
                        'Measure', 'Verify savings']) {
      expect(screen.getByRole('heading', { name: step })).toBeInTheDocument();
    }
  });
});

describe('accessibility', () => {
  it('scrolls wide tables inside their own container, not the page', () => {
    const { container } = renderDemo();

    for (const table of Array.from(container.querySelectorAll('table'))) {
      expect(table.closest('.psassets__scroll')).not.toBeNull();
    }
  });

  it('gives every table a caption naming what it holds', () => {
    const { container } = renderDemo();

    for (const table of Array.from(container.querySelectorAll('table'))) {
      expect(table.querySelector('caption')?.textContent).toBeTruthy();
    }
  });

  it('makes the asset picker a real button, not a clickable row', () => {
    const { container } = renderDemo();
    const rows = container.querySelectorAll('.pstable tbody tr');

    expect(rows.length).toBeGreaterThan(0);
    for (const row of Array.from(rows)) {
      expect(row.getAttribute('onclick')).toBeNull();
    }
  });

  it('starts at h2, because it is a section and not a page', () => {
    const { container } = renderDemo();
    const first = container.querySelector('h1, h2, h3, h4, h5');

    expect(first?.tagName).toBe('H2');
    expect(container.querySelector('h1')).toBeNull();
  });
});
