import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import About from './About';

describe('About describes today, not the roadmap', () => {
  it('explains the three concepts an assessment rests on', () => {
    render(<About />);
    for (const term of [/^Provenance/, /^Evidence Coverage/, /^Confidence/]) {
      expect(screen.getByText(term, { exact: false })).toBeInTheDocument();
    }
  });

  it('says plainly that no organisation has a published score', () => {
    render(<About />);
    expect(screen.getByText(/No organisation currently has a published score/i))
      .toBeInTheDocument();
  });

  it('names the four verticals as direction, not capability', () => {
    render(<About />);
    expect(screen.getByText(/None of those decision engines is implemented/i))
      .toBeInTheDocument();
  });

  it('claims no customers and shows no logos', () => {
    const { container } = render(<About />);
    expect(screen.getByText(/no enterprise customers to name yet/i))
      .toBeInTheDocument();
    expect(container.querySelectorAll('img')).toHaveLength(0);
  });

  it('publishes no counter', () => {
    // Every number on a public page has to come from the single source of
    // truth. A prose page cannot have one, so it states no counts at all.
    const { container } = render(<About />);
    expect(container.textContent).not.toMatch(/\b\d{2,}\+?\s+(companies|countries|organisations|clients)/i);
  });

  it('does not promise a score unconditionally', () => {
    const { container } = render(<About />);
    expect(container.textContent).toMatch(
      /publishes an assessment only where that evidence supports one/i);
  });
});
