import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { Nav } from './Nav';

function renderNav() {
  return render(
    <MemoryRouter>
      <Nav />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
    ok: true, status: 200,
    json: async () => ({ authenticated: false, username: null, is_staff: false }),
  }));
});

describe('primary navigation', () => {
  it('shows exactly the five canonical destinations', async () => {
    renderNav();
    const nav = screen.getByRole('navigation', { name: /primary/i });

    for (const label of ['Intelligence', 'Projects', 'Eco Tours', 'About', 'Contact']) {
      expect(within(nav).getByRole('link', { name: label })).toBeInTheDocument();
    }
  });

  it('does not promote superseded destinations', async () => {
    renderNav();
    const nav = screen.getByRole('navigation', { name: /primary/i });

    // These are either experiments (Labs), internal, or a data directory —
    // none of them describes what the product is.
    for (const label of ['Rankings', 'Countries', 'AI Agents', 'Compendium',
                         'Framework', 'Methodology', 'Geo Intelligence']) {
      expect(within(nav).queryByRole('link', { name: label })).toBeNull();
    }
  });

  it('keeps Companies reachable but not primary', async () => {
    renderNav();
    const link = screen.getByRole('link', { name: 'Companies' });

    expect(link).toBeInTheDocument();
    expect(link.className).toContain('nav__link--minor');
  });

  it('keeps Labs reachable as a secondary destination', async () => {
    renderNav();

    expect(screen.getByRole('link', { name: 'EcoIQ Labs' }).className)
      .toContain('nav__link--minor');
  });
});

describe('accessibility', () => {
  it('exposes the toggle state', async () => {
    renderNav();
    const toggle = screen.getByRole('button');

    expect(toggle).toHaveAttribute('aria-expanded', 'false');
    await userEvent.click(toggle);
    expect(toggle).toHaveAttribute('aria-expanded', 'true');
  });

  it('labels the toggle for screen readers', async () => {
    renderNav();

    expect(screen.getByText(/open menu/i)).toBeInTheDocument();
  });

  it('closes on Escape', async () => {
    renderNav();
    const toggle = screen.getByRole('button');
    await userEvent.click(toggle);
    expect(toggle).toHaveAttribute('aria-expanded', 'true');

    await userEvent.keyboard('{Escape}');

    expect(toggle).toHaveAttribute('aria-expanded', 'false');
  });

  it('closes when a destination is chosen', async () => {
    renderNav();
    const toggle = screen.getByRole('button');
    await userEvent.click(toggle);

    await userEvent.click(screen.getByRole('link', { name: 'Projects' }));

    expect(toggle).toHaveAttribute('aria-expanded', 'false');
  });

  it('names the navigation landmark', async () => {
    renderNav();

    expect(screen.getByRole('navigation', { name: /primary/i })).toBeInTheDocument();
  });
});

describe('session affordance', () => {
  it('offers sign-in to an anonymous visitor', async () => {
    renderNav();

    expect(await screen.findByRole('link', { name: /sign in/i })).toBeInTheDocument();
  });

  it('shows the username instead once signed in', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true, status: 200,
      json: async () => ({ authenticated: true, username: 'alice', is_staff: false }),
    }));
    renderNav();

    expect(await screen.findByText('alice')).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: /sign in/i })).toBeNull();
  });

  it('marks a staff session', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true, status: 200,
      json: async () => ({ authenticated: true, username: 'staffer', is_staff: true }),
    }));
    renderNav();

    // `staffer` also matches /staff/, so assert on the marker specifically.
    expect(await screen.findByText('· staff')).toBeInTheDocument();
  });
});
