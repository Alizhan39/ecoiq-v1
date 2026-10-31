import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Tours from './Tours';

function show() {
  return render(<MemoryRouter><Tours /></MemoryRouter>);
}

describe('Eco Tours', () => {
  it('states the product is interest capture, not booking', () => {
    show();

    expect(screen.getByText(/no booking or\s+payment yet/i)).toBeInTheDocument();
  });

  it('offers no booking affordance', () => {
    show();

    // A booking form that cannot book is a lie with a submit button.
    expect(screen.queryByRole('button', { name: /book/i })).toBeNull();
    expect(screen.queryByRole('textbox', { name: /date/i })).toBeNull();
  });

  it('does not invent availability', () => {
    const { container } = show();

    expect(container.textContent).not.toMatch(/places remaining/i);
    expect(container.textContent).not.toMatch(/departs/i);
  });

  it('marks its status honestly', () => {
    show();

    expect(screen.getByText('Beta')).toBeInTheDocument();
  });

  it('gives a way to register interest that works today', () => {
    show();

    expect(screen.getByRole('link', { name: /Tell us where to run the first one/i }))
      .toHaveAttribute('href', '/contact');
  });

  it('publishes no invented contact address', () => {
    // An earlier version sent people to hello@ecoiq.uk, which appears nowhere
    // else in the repository and which nothing shows to exist. An invented
    // contact route is worse than an invented number: someone writes to it.
    const { container } = show();
    expect(container.innerHTML).not.toContain('hello@ecoiq.uk');
  });

  it('links to the full programme rather than restating it', () => {
    show();
    expect(screen.getByRole('link', { name: /Khalifa Stewardship Tours/i }))
      .toHaveAttribute('href', '/khalifa-tours/');
  });
});
