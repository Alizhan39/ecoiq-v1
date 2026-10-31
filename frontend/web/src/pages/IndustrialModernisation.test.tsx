/**
 * The product page, held to the claims it is allowed to make.
 *
 * The load-bearing property: the plant transformation and the EcoIQ workflow
 * are TWO axes and must never read as one seven-step sequence. Everything else
 * here is a product-truth rule with a test attached, because each of them has
 * previously been broken somewhere in this codebase by a confident-looking
 * piece of markup.
 */
import { render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import IndustrialModernisation from './IndustrialModernisation';
import { WORKFLOW } from '@/features/transition/domain/capabilities';
import { STAGES } from '@/features/transition/model/stages';

function renderPage() {
  return render(
    <MemoryRouter><IndustrialModernisation /></MemoryRouter>,
  );
}

describe('two axes, never merged', () => {
  it('shows the eight physical stages and the seven workflow stages', () => {
    renderPage();
    for (const stage of STAGES) {
      expect(screen.getAllByText(stage.label).length,
        `physical stage ${stage.key}`).toBeGreaterThan(0);
    }
    for (const stage of WORKFLOW) {
      expect(screen.getAllByText(stage.label).length,
        `workflow stage ${stage.key}`).toBeGreaterThan(0);
    }
  });

  it('puts the four physical interventions INSIDE engineer, not beside it', () => {
    const { container } = renderPage();
    const steps = [...container.querySelectorAll('.itworkflow__step')];
    const engineer = steps.find((s) => s.querySelector('h3')?.textContent === 'Engineer')!;
    const contained = engineer.querySelector('.itworkflow__contains')!;
    const labels = [...contained.querySelectorAll('li')].map((n) => n.textContent);
    expect(labels).toEqual(['Retrofit', 'Electrify', 'Recover', 'Circularise']);
  });

  it('no other workflow stage contains a physical stage', () => {
    const { container } = renderPage();
    const withContained = [...container.querySelectorAll('.itworkflow__step')]
      .filter((s) => s.querySelector('.itworkflow__contains'))
      .map((s) => s.querySelector('h3')?.textContent);
    expect(withContained).toEqual(['Engineer']);
  });

  it('the two axes live under separate headings', () => {
    renderPage();
    // If they shared one, a reader would be entitled to read one sequence.
    expect(screen.getByRole('heading', { name: /How EcoIQ works/i }))
      .toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /step by step/i }))
      .toBeInTheDocument();
  });
});

describe('capability status is stated, not implied', () => {
  it('every workflow stage shows its status', () => {
    const { container } = renderPage();
    const statuses = [...container.querySelectorAll('.itworkflow__status')]
      .map((n) => n.textContent);
    expect(statuses).toHaveLength(WORKFLOW.length);
    for (const s of statuses) {
      expect(['EXPERIMENTAL', 'PLANNED', 'SPECIFICATION']).toContain(s);
    }
  });

  it('nothing claims to be production or beta', () => {
    const { container } = renderPage();
    const text = container.textContent ?? '';
    expect(text).not.toMatch(/\bPRODUCTION\b/);
    expect(text).not.toMatch(/\bBETA\b/);
  });

  it('every status carries a basis a reader can open', () => {
    const { container } = renderPage();
    expect(container.querySelectorAll('.itworkflow__basis'))
      .toHaveLength(WORKFLOW.length);
  });

  it('says plainly that none of the workflow runs against a real facility', () => {
    renderPage();
    expect(screen.getByText(/None of these stages runs against a real facility/i))
      .toBeInTheDocument();
  });
});

describe('the five product truths', () => {
  it('does not present the visualisation as a live capability', () => {
    renderPage();
    // Twice, deliberately: once under the hero and once with the narrative.
    // A reader who skips one meets the other.
    expect(screen.getAllByText(/describes no specific facility/i).length)
      .toBeGreaterThanOrEqual(2);
    expect(screen.getByText(/EcoIQ has no facility ingestion/i)).toBeInTheDocument();
  });

  it('does not treat electrification as decarbonisation', () => {
    renderPage();
    expect(screen.getByText(/does not by itself reduce emissions/i))
      .toBeInTheDocument();
  });

  it('shows no percentage or invented figure anywhere', () => {
    const { container } = renderPage();
    const text = container.textContent ?? '';
    expect(text).not.toMatch(/\d+\s*%/);
    // A FIGURE, not the word. "payback" appears three times on this page and
    // every one of them denies having one — "no capital cost, saving, payback
    // or emissions figure exists". Forbidding the vocabulary would forbid
    // saying what is absent, which is the opposite of the rule.
    expect(text).not.toMatch(/payback[^.]{0,20}\d/i);
    expect(text).not.toMatch(/[£$€]\s?\d/);
    expect(text).not.toMatch(/\d+\s*(kWh|MWh|tCO2|tonnes|years?\b)/i);
  });

  it('separates architecture support from production ingestion', () => {
    const { container } = renderPage();
    const table = container.querySelector('.itdata__table')!;
    const headers = [...table.querySelectorAll('th[scope="col"]')]
      .map((n) => n.textContent);
    expect(headers).toContain('Architecture supports');
    expect(headers).toContain('Production ingestion');
    // And every row reports nothing collected.
    const cells = [...table.querySelectorAll('.itdata__no')].map((n) => n.textContent);
    expect(cells.length).toBeGreaterThan(5);
    expect(new Set(cells)).toEqual(new Set(['None']));
  });

  it('does not lead with a rating, a score, or an organisation', () => {
    renderPage();
    const h1 = screen.getByRole('heading', { level: 1 }).textContent ?? '';
    expect(h1).not.toMatch(/score|rating|ESG|company/i);
    expect(h1).toMatch(/losses/i);
  });
});

describe('the call to action matches what exists', () => {
  it('invites a conversation rather than an analysis run', () => {
    renderPage();
    expect(screen.getByRole('link', { name: /Discuss a facility/i }))
      .toBeInTheDocument();
  });

  it('never offers to analyse the reader\'s facility', () => {
    const { container } = renderPage();
    expect(container.textContent ?? '').not.toMatch(/analyse your facility/i);
  });
});

describe('the 114 principles are supporting, not central', () => {
  it('mentions them below the industrial content, as a governance layer', () => {
    const { container } = renderPage();
    const principles = container.querySelector('.itpage__principles')!;
    const workflow = container.querySelector('.itworkflow')!;
    expect(workflow.compareDocumentPosition(principles)
      & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(within(principles as HTMLElement)
      .getByText(/governance and evidence layer/i)).toBeInTheDocument();
  });

  it('says no principle mapping has been recorded', () => {
    renderPage();
    expect(screen.getByText(/No principle mapping has been recorded/i))
      .toBeInTheDocument();
  });
});

describe('photography', () => {
  it('leaves explicit slots rather than filling them with stock imagery', () => {
    const { container } = renderPage();
    const slots = container.querySelectorAll('.itpage__imageslot');
    expect(slots.length).toBeGreaterThanOrEqual(3);
    expect(slots.length).toBeLessThanOrEqual(5);
  });

  it('every slot names its subject and what would be wrong', () => {
    const { container } = renderPage();
    for (const slot of container.querySelectorAll('.itpage__imageslot')) {
      expect(slot.textContent).toMatch(/Photography needed/);
      expect(slot.textContent).toMatch(/Avoid:/);
    }
  });

  it('ships no image asset at all', () => {
    const { container } = renderPage();
    expect(container.querySelectorAll('img')).toHaveLength(0);
  });
});

describe('heading structure', () => {
  it('has one H1 and never skips a level', () => {
    const { container } = renderPage();
    const levels = [...container.querySelectorAll('h1,h2,h3,h4,h5,h6')]
      .map((h) => Number(h.tagName[1]));
    expect(levels.filter((l) => l === 1)).toHaveLength(1);
    const skips: string[] = [];
    for (let i = 1; i < levels.length; i += 1) {
      const prev = levels[i - 1]!; const cur = levels[i]!;
      if (cur - prev > 1) skips.push(`H${prev} -> H${cur}`);
    }
    expect(skips).toEqual([]);
  });
});
