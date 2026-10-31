import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { KhalifahPanel } from './KhalifahPanel';
import type { KpiInvestigation } from '@/types/kpi';

function investigation(over: Partial<KpiInvestigation> = {}): KpiInvestigation {
  return {
    company: { slug: 'testco', name: 'Testco', sector: 'retail' },
    stewardship_principle: {
      kpi_id: 103, title: 'Time Risk & Transition Urgency',
      tagline: 'tagline',
      question: 'Does the pace of ESG improvement match what is required?',
      category: 'risk', principle_statement: 'statement',
      metrics: ['transition plan milestone adherence', 'emissions trajectory vs target'],
    },
    assessment: {
      verdict: 'support', verdict_label: 'SUPPORTS', confidence: 'MEDIUM',
      confidence_reasons: ['One item was reviewed beyond ingestion.'],
      rationale: 'One confirmed supporting item.', is_demo: false,
      last_assessed_at: null,
    },
    counts: {
      total: 1, confirmed: 1, supports: 1, conflicts: 0, context: 0,
      excluded_from_assessment: 0, remediation_steps: 0,
    },
    evidence: [], remediation: [],
    ...over,
  } as KpiInvestigation;
}

async function openPanel(name: RegExp) {
  await userEvent.click(screen.getByRole('button', { name }));
}

describe('Khalifah speaks about the principle in front of it', () => {
  it('names this principle\'s own indicators, not another\'s', async () => {
    /**
     * The regression this pins: these lists were written for principle #114
     * and rendered for every principle. Once the matrix linked all 114,
     * "Time Risk & Transition Urgency" was advising the organisation to keep
     * security warnings proportionate — App Store guidance, on a principle
     * about the pace of transition.
     */
    render(<KhalifahPanel inv={investigation()} />);
    await openPanel(/strengthen/i);
    expect(screen.getByText('transition plan milestone adherence')).toBeInTheDocument();
    expect(screen.getByText('emissions trajectory vs target')).toBeInTheDocument();
  });

  it('carries none of the principle-114 language', async () => {
    const { container } = render(<KhalifahPanel inv={investigation()} />);
    for (const panel of [/strengthen/i, /challenge/i, /why/i, /produced/i]) {
      await openPanel(panel);
    }
    const text = container.textContent ?? '';
    for (const leak of [/security warning/i, /switching.friction/i,
      /alternatives are presented/i, /default path/i]) {
      expect(text).not.toMatch(leak);
    }
  });

  it('frames strengthening as evidence, not advice to the organisation', async () => {
    /**
     * EcoIQ reports what it can conclude. Telling an organisation what to do
     * is a different product, and stating it beside a finding invites reading
     * the finding as a demand.
     */
    render(<KhalifahPanel inv={investigation()} />);
    await openPanel(/strengthen/i);
    expect(screen.getByText(/not advice to the organisation/i)).toBeInTheDocument();
  });

  it('says so when the registry records no indicators', async () => {
    const inv = investigation();
    inv.stewardship_principle.metrics = [];
    render(<KhalifahPanel inv={inv} />);
    await openPanel(/strengthen/i);
    expect(screen.getByText(/no measurable indicators for this principle/i))
      .toBeInTheDocument();
    expect(screen.getByText(/gap in the framework/i)).toBeInTheDocument();
  });

  it('counts excluded evidence exactly when there is some', async () => {
    render(<KhalifahPanel inv={investigation({
      counts: {
        total: 4, confirmed: 1, supports: 1, conflicts: 0, context: 0,
        excluded_from_assessment: 3, remediation_steps: 0,
      },
    })} />);
    await openPanel(/challenge/i);
    expect(screen.getByText(/3 items currently excluded are/i)).toBeInTheDocument();
  });

  it('does not invent excluded evidence when there is none', async () => {
    render(<KhalifahPanel inv={investigation()} />);
    await openPanel(/challenge/i);
    expect(screen.getByText(/Evidence not yet linked to this principle/i))
      .toBeInTheDocument();
  });

  it('says an unopposed conclusion is the weaker kind', async () => {
    render(<KhalifahPanel inv={investigation()} />);
    await openPanel(/strengthen/i);
    expect(screen.getByText(/weaker than one that survived disagreement/i))
      .toBeInTheDocument();
  });

  it('reports no assessment when nothing is confirmed', async () => {
    render(<KhalifahPanel inv={investigation({
      counts: {
        total: 2, confirmed: 0, supports: 0, conflicts: 0, context: 0,
        excluded_from_assessment: 2, remediation_steps: 0,
      },
    })} />);
    expect(screen.getByText(/no assessment has been made/i)).toBeInTheDocument();
  });

  it('states that the verdict is derived by rule, not generated', async () => {
    render(<KhalifahPanel inv={investigation()} />);
    await openPanel(/produced/i);
    expect(screen.getByText(/not asserted, and not model-generated/i))
      .toBeInTheDocument();
  });
});
