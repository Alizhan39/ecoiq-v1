/**
 * The semantic layer as rendered, checked as content rather than as markup.
 *
 * The question each test asks: could a reader who cannot see the drawing
 * follow the argument from this alone?
 */
import { render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { TransitionNarrative } from './TransitionNarrative';

describe('the narrative is readable without the picture', () => {
  it('names every step of the sequence, at any scroll position', () => {
    render(<TransitionNarrative progress={0} />);
    for (const label of ['Legacy system', 'Diagnose', 'Retrofit', 'Electrify',
      'Recover', 'Circularise', 'Optimise', 'Verify']) {
      expect(screen.getByRole('heading', { name: label })).toBeInTheDocument();
    }
  });

  it('lists the steps in an ordered list, because the order is the argument', () => {
    const { container } = render(<TransitionNarrative progress={0.5} />);
    const list = container.querySelector('ol.transition-narrative__steps');
    expect(list).toBeTruthy();
    expect(list!.querySelectorAll(':scope > li')).toHaveLength(8);
  });

  it('shows all steps at progress 0, not just the first', () => {
    // A reader using a screen reader does not scroll to read. Revealing steps
    // progressively would make the content depend on a gesture they are not
    // making.
    const { container } = render(<TransitionNarrative progress={0} />);
    expect(container.querySelectorAll('.transition-narrative__step'))
      .toHaveLength(8);
  });

  it('marks the current step for assistive technology', () => {
    const { container } = render(<TransitionNarrative progress={0.5} />);
    const current = container.querySelectorAll('[aria-current="step"]');
    expect(current).toHaveLength(1);
  });

  it('moves the current step as progress advances', () => {
    const { container, rerender } = render(<TransitionNarrative progress={0} />);
    const first = container.querySelector('[aria-current="step"]')!.textContent;
    rerender(<TransitionNarrative progress={1} />);
    const last = container.querySelector('[aria-current="step"]')!.textContent;
    expect(last).not.toBe(first);
    expect(last).toContain('Verify');
  });

  it('explains the physical change, not the visual one', () => {
    render(<TransitionNarrative progress={1} />);
    expect(screen.getAllByRole('heading', { name: 'What changes physically' })
      .length).toBeGreaterThanOrEqual(5);
  });
});

describe('the narrative claims nothing it cannot support', () => {
  it('leads with the disclaimer rather than burying it', () => {
    const { container } = render(<TransitionNarrative progress={0} />);
    const disclaimer = container.querySelector('.transition-narrative__disclaimer');
    const firstStep = container.querySelector('.transition-narrative__step');
    expect(disclaimer).toBeTruthy();
    // Appears before the content it qualifies, in document order.
    expect(disclaimer!.compareDocumentPosition(firstStep!)
      & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it('says the illustration describes no specific facility', () => {
    render(<TransitionNarrative progress={0} />);
    expect(screen.getByText(/describes no specific facility/i)).toBeInTheDocument();
  });

  it('renders every loss magnitude as an em dash, never a number', () => {
    const { container } = render(<TransitionNarrative progress={1} />);
    const table = container.querySelector('.transition-narrative__losses')!;
    const cells = within(table as HTMLElement).getAllByRole('cell');
    const magnitudes = cells.filter((c) => c.textContent === '—');
    expect(magnitudes.length).toBeGreaterThanOrEqual(5);
  });

  it('shows no percentage anywhere', () => {
    const { container } = render(<TransitionNarrative progress={0.63} />);
    expect(container.textContent).not.toMatch(/\d+\s*%/);
  });

  it('states that no outcome figure exists', () => {
    render(<TransitionNarrative progress={1} />);
    // Twice, deliberately: once where the Verify step explains why measurement
    // matters, and once in the outcome itself. A reader who skips one meets
    // the other, and the two must not disagree.
    const said = screen.getAllByText(/unknown rather than zero/i);
    expect(said.length).toBe(2);
  });

  it('states that nothing has been verified', () => {
    render(<TransitionNarrative progress={1} />);
    expect(screen.getByText(/Not verified/i)).toBeInTheDocument();
  });

  it('gives the loss table a caption explaining the em dashes', () => {
    const { container } = render(<TransitionNarrative progress={0} />);
    const caption = container.querySelector('caption');
    expect(caption?.textContent).toMatch(/naming a loss is not the same/i);
  });
});

describe('heading structure', () => {
  it('starts at H2 so it nests under a page H1', () => {
    const { container } = render(<TransitionNarrative progress={0} />);
    const levels = [...container.querySelectorAll('h1,h2,h3,h4,h5,h6')]
      .map((h) => Number(h.tagName[1]));
    expect(levels[0]).toBe(2);
    expect(levels).not.toContain(1);
  });

  it('never skips a heading level', () => {
    const { container } = render(<TransitionNarrative progress={1} />);
    const levels = [...container.querySelectorAll('h1,h2,h3,h4,h5,h6')]
      .map((h) => Number(h.tagName[1]));
    const skips: string[] = [];
    for (let i = 1; i < levels.length; i += 1) {
      const previous = levels[i - 1]!;
      const current = levels[i]!;
      if (current - previous > 1) skips.push(`H${previous} -> H${current}`);
    }
    expect(skips).toEqual([]);
  });

  it('is labelled by its own heading', () => {
    const { container } = render(<TransitionNarrative progress={0} />);
    const section = container.querySelector('section');
    const id = section?.getAttribute('aria-labelledby');
    expect(id).toBeTruthy();
    expect(container.querySelector(`#${id}`)).toBeTruthy();
  });
});
