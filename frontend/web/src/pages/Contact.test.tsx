import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import Contact from './Contact';

/**
 * The form's job is to reach a real endpoint with the real anti-abuse fields.
 * These tests assert the payload, because the failure that matters here is a
 * silently omitted honeypot or form token — the form would still look and feel
 * correct while being exactly as open as the endpoint that produced 924 spam
 * notifications in one incident.
 */

function mockApi(post: { ok: boolean; status?: number; body?: unknown }) {
  const fetchMock = vi.fn(async (_url: string, init?: RequestInit) => {
    if ((init?.method ?? 'GET') === 'GET') {
      return {
        ok: true, status: 200,
        json: async () => ({ form_token: 'tok-123', turnstile_site_key: '' }),
      };
    }
    return {
      ok: post.ok, status: post.status ?? 200,
      json: async () => post.body ?? { status: 'received', detail: 'ok' },
    };
  });
  vi.stubGlobal('fetch', fetchMock);
  return fetchMock;
}

async function fillIn() {
  const user = userEvent.setup();
  await user.type(screen.getByLabelText(/^Name/), 'Ada');
  await user.type(screen.getByLabelText(/^Email/), 'ada@example.com');
  await user.type(
    screen.getByLabelText(/^Message/),
    'This is a long enough enquiry message to pass validation.');
  return user;
}

beforeEach(() => vi.restoreAllMocks());

describe('the enquiry form', () => {
  it('submits to the real endpoint', async () => {
    const fetchMock = mockApi({ ok: true });
    render(<Contact />);
    const user = await fillIn();
    await user.click(screen.getByRole('button', { name: /Send message/i }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        '/api/v2/contact/', expect.objectContaining({ method: 'POST' }));
    });
  });

  it('carries the honeypot and the signed form token', async () => {
    const fetchMock = mockApi({ ok: true });
    render(<Contact />);
    await waitFor(() => expect(fetchMock).toHaveBeenCalled());  // the GET
    const user = await fillIn();
    await user.click(screen.getByRole('button', { name: /Send message/i }));

    await waitFor(() => {
      const post = fetchMock.mock.calls.find(
        ([, init]) => (init as RequestInit | undefined)?.method === 'POST');
      expect(post).toBeDefined();
      const body = JSON.parse((post![1] as RequestInit).body as string);
      expect(body.form_token).toBe('tok-123');
      expect(body).toHaveProperty('website', '');
    });
  });

  it('confirms receipt without claiming more than it knows', async () => {
    mockApi({ ok: true });
    render(<Contact />);
    const user = await fillIn();
    await user.click(screen.getByRole('button', { name: /Send message/i }));

    expect(await screen.findByText(/Message received/i)).toBeInTheDocument();
  });

  it('shows field errors from the server rather than a generic failure',
    async () => {
      mockApi({
        ok: false, status: 400,
        body: { errors: { email: 'A valid email address is required.' } },
      });
      render(<Contact />);
      const user = await fillIn();
      await user.click(screen.getByRole('button', { name: /Send message/i }));

      expect(await screen.findByText(/A valid email address is required/))
        .toBeInTheDocument();
    });

  it('tells a throttled sender what actually happened', async () => {
    // "Something went wrong" for a rate limit sends the sender straight back
    // to resubmitting, which is the one thing that makes it worse.
    mockApi({ ok: false, status: 429 });
    render(<Contact />);
    const user = await fillIn();
    await user.click(screen.getByRole('button', { name: /Send message/i }));

    expect(await screen.findByText(/Too many submissions/i)).toBeInTheDocument();
  });

  it('keeps the honeypot out of the accessibility tree', () => {
    mockApi({ ok: true });
    const { container } = render(<Contact />);
    const honeypot = container.querySelector('#website');

    expect(honeypot).not.toBeNull();
    expect(honeypot!.closest('[aria-hidden="true"]')).not.toBeNull();
    expect(honeypot!.getAttribute('tabindex')).toBe('-1');
  });

  it('invents no offices, phone numbers or customer counts', () => {
    mockApi({ ok: true });
    const { container } = render(<Contact />);
    const text = container.textContent ?? '';

    expect(text).not.toMatch(/\+\d{1,3}[\s\d()-]{7,}/);   // phone number
    expect(text).not.toMatch(/\b(headquarters|offices in)\b/i);
    expect(text).toMatch(/alizhan@ecoiq\.uk/);
  });
});
