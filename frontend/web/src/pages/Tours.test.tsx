import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import Tours from './Tours';

describe('Eco Tours', () => {
  it('states the product is interest capture, not booking', () => {
    render(<Tours />);

    expect(screen.getByText(/no booking or\s+payment yet/i)).toBeInTheDocument();
  });

  it('offers no booking affordance', () => {
    render(<Tours />);

    // A booking form that cannot book is a lie with a submit button.
    expect(screen.queryByRole('button', { name: /book/i })).toBeNull();
    expect(screen.queryByRole('textbox', { name: /date/i })).toBeNull();
  });

  it('does not invent availability', () => {
    const { container } = render(<Tours />);

    expect(container.textContent).not.toMatch(/places remaining/i);
    expect(container.textContent).not.toMatch(/departs/i);
  });

  it('marks its status honestly', () => {
    render(<Tours />);

    expect(screen.getByText('Beta')).toBeInTheDocument();
  });

  it('gives a way to register interest that works today', () => {
    render(<Tours />);

    expect(screen.getByRole('link', { name: /hello@ecoiq\.uk/ }))
      .toHaveAttribute('href', 'mailto:hello@ecoiq.uk');
  });
});
