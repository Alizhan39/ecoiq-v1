import { describe, expect, it } from 'vitest';
import { ROUTE_TITLES, titleFor } from './documentTitle';

/**
 * Found in production verification: clicking a nav link changed the page but
 * left the tab reading the previous route's title, because client-side
 * navigation replaces no document and Django's injected <title> stays put.
 */
describe('route titles', () => {
  it('titles a known route', () => {
    expect(titleFor('/intelligence')).toBe('Intelligence — EcoIQ');
  });

  it('ignores a trailing slash', () => {
    expect(titleFor('/trust/')).toBe(titleFor('/trust'));
  });

  it('titles the homepage', () => {
    expect(titleFor('/')).toBe(ROUTE_TITLES['/']);
  });

  it('leaves a concept page to the server', () => {
    // Its title is the concept's own name, which the server already injected.
    // Replacing it with a generic one would be worse than doing nothing.
    expect(titleFor('/projects/almaty-clean-air')).toBeNull();
  });

  it('still titles the projects index itself', () => {
    expect(titleFor('/projects')).toBe('Projects — EcoIQ');
  });

  it('leaves one principle to the server', () => {
    /**
     * core.spa.principle_spa_view puts '#57 Iron & Infrastructure
     * Responsibility' in the document and 404s outside 1-114. Before this,
     * every principle page read 'Page not found' in the tab while showing the
     * principle perfectly well — caught in browser verification, not by a
     * test, because the route-key guard only compares the static maps.
     */
    expect(titleFor('/principles/57')).toBeNull();
    expect(titleFor('/principles/57/')).toBeNull();
  });

  it('still titles the principles index itself', () => {
    expect(titleFor('/principles')).toBe('The 114 stewardship principles — EcoIQ');
  });

  it('reads as not-found for a route that does not exist', () => {
    expect(titleFor('/no-such-page')).toBe('Page not found — EcoIQ');
  });

  it('gives every title the EcoIQ suffix', () => {
    for (const title of Object.values(ROUTE_TITLES)) {
      expect(title).toMatch(/EcoIQ/);
    }
  });

  it('gives no two routes the same title', () => {
    const titles = Object.values(ROUTE_TITLES);
    expect(new Set(titles).size).toBe(titles.length);
  });
});
