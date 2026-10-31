import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { HowItWorks } from './HowItWorks';

beforeEach(() => {
  // jsdom has neither, and the component must not depend on them existing.
  vi.stubGlobal('IntersectionObserver', class {
    observe() {} unobserve() {} disconnect() {}
  });
  vi.stubGlobal('ResizeObserver', class {
    observe() {} unobserve() {} disconnect() {}
  });
});

describe('how it works', () => {
  it('states every running stage as text', async () => {
    /**
     * The list is the primary. If these ever moved into the canvas alone, a
     * screen reader, a crawler and anyone with JavaScript off would lose them.
     */
    render(<HowItWorks />);
    for (const stage of ['Evidence', 'Assessment', 'Provenance',
      'Coverage', 'Confidence', 'Decision']) {
      expect(screen.getByText(stage)).toBeInTheDocument();
    }
  });

  it('hides the decorative canvas from assistive technology', async () => {
    const { container } = render(<HowItWorks />);
    const decoration = container.querySelector('.pipeline-canvas');
    expect(decoration).toHaveAttribute('aria-hidden', 'true');
  });

  it('renders the list even when canvas is unavailable', () => {
    /**
     * getContext returns null in jsdom. The component must degrade to the
     * list rather than throwing, because that is also what an old browser or
     * a blocked canvas does.
     */
    render(<HowItWorks />);
    expect(screen.getByRole('list')).toBeInTheDocument();
    expect(screen.getAllByRole('listitem')).toHaveLength(6);
  });

  it('keeps the unimplemented loop separate from the running pipeline', async () => {
    /**
     * Presenting an unimplemented stage beside an implemented one in the same
     * styling is how a roadmap becomes a claim.
     */
    render(<HowItWorks />);
    expect(screen.getByText(/not running today/i)).toBeInTheDocument();
    expect(screen.getByText(/In development/i)).toBeInTheDocument();
  });

  it('says plainly that most evidence publishes nothing', async () => {
    /** The sentence the drawing exists to illustrate. */
    render(<HowItWorks />);
    expect(screen.getByText(/Most evidence does not carry a publishable conclusion/i))
      .toBeInTheDocument();
  });

  it('claims no agent, sensor or continuous monitoring', () => {
    /**
     * The cinematic work this canvas ports its technique from drew specialist
     * agents, sensor networks and overnight runs. platform_registry says EcoIQ
     * has no PRODUCTION AI agents and render.yaml has no worker; none of it
     * may come back in pictures or in words.
     */
    const { container } = render(<HowItWorks />);
    const text = container.textContent ?? '';
    for (const claim of [/\bagents?\b/i, /sensor/i, /overnight/i,
      /continuous/i, /real[- ]time/i, /autonomous/i]) {
      expect(text).not.toMatch(claim);
    }
  });
});
