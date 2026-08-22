import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, within } from '@testing-library/react';
import { App } from './App';

beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
    ok: true, status: 200,
    json: async () => ({ authenticated: false, username: null, is_staff: false }),
  }));
});

function footer() {
  const { container } = render(<App />);
  const element = container.querySelector('footer');
  expect(element).not.toBeNull();
  return element!;
}

describe('the footer', () => {
  it('keeps the GCC investor entry point', () => {
    // /gcc-investors/ fronts eight sitemap-registered pages, and the footer is
    // their only internal link. It used to be linked from the server-rendered
    // homepage and from /pricing/ — both are React now, so dropping it here
    // would orphan all eight.
    expect(within(footer()).getByRole('link', { name: /GCC investors/i }))
      .toHaveAttribute('href', '/gcc-investors/');
  });

  it('links Django-served sections with plain anchors, not client routes', () => {
    // A <Link> would render a React page on click and a Django page on
    // refresh — the same URL behaving two ways depending on how you got there.
    for (const href of ['/companies/', '/gcc-investors/']) {
      const link = footer().querySelector(`a[href="${href}"]`);
      expect(link).not.toBeNull();
    }
  });

  it('does not grow back into a second navigation tree', () => {
    expect(footer().querySelectorAll('a').length).toBeLessThanOrEqual(10);
  });

  it('invents no legal pages EcoIQ does not have', () => {
    const html = footer().innerHTML;
    for (const absent of ['/privacy/', '/terms/', '/cookies/']) {
      expect(html).not.toContain(absent);
    }
  });

  it('states the evidence rule on every page', () => {
    expect(footer().textContent)
      .toMatch(/only where evidence supports them/i);
  });
});
