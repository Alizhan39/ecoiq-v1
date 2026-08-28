import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { ErrorState } from './States';

/**
 * Production showed a visitor "GET /api/v2/companies/?page=1 failed with 429"
 * on the organisations page. Two defects in one line: an internal request line
 * printed at a reader, and a rate limit presented as a broken page when the
 * data was fine and the answer was "wait a moment".
 */
function withStatus(status: number, message = 'GET /api/v2/companies/ failed') {
  const error = new Error(message) as Error & { status: number };
  error.status = status;
  return error;
}

describe('the error state', () => {
  it('never prints the internal request line at a reader', () => {
    const { container } = render(<ErrorState error={withStatus(429)} />);
    expect(container.textContent).not.toMatch(/GET \/api/);
    expect(container.textContent).not.toMatch(/failed with/);
  });

  it('treats a rate limit as "wait", not as a broken page', () => {
    render(<ErrorState error={withStatus(429)} />);
    expect(screen.getByText(/Too many requests/i)).toBeInTheDocument();
    expect(screen.getByText(/Nothing is wrong with the data/i)).toBeInTheDocument();
  });

  it('says a 403 may need sign-in rather than blaming the data', () => {
    render(<ErrorState error={withStatus(403)} />);
    expect(screen.getByText(/not available to view/i)).toBeInTheDocument();
  });

  it('says a 404 is not on record', () => {
    render(<ErrorState error={withStatus(404)} />);
    expect(screen.getByText(/not on record/i)).toBeInTheDocument();
  });

  it('owns a server failure rather than implying the evidence is wrong', () => {
    render(<ErrorState error={withStatus(503)} />);
    expect(screen.getByText(/could not answer just now/i)).toBeInTheDocument();
    expect(screen.getByText(/not in the evidence/i)).toBeInTheDocument();
  });

  it('falls back safely when there is no status at all', () => {
    render(<ErrorState error={new Error('boom')} />);
    expect(screen.getByText(/Could not load this section/i)).toBeInTheDocument();
    expect(screen.queryByText('boom')).not.toBeInTheDocument();
  });

  it('announces itself to assistive technology', () => {
    render(<ErrorState error={withStatus(500)} />);
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });
});
