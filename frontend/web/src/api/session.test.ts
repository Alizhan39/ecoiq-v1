import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ANONYMOUS } from '@/types/session';

describe('the session contract', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    document.cookie = '';
  });

  it('treats anonymous as a real state, not an error', () => {
    expect(ANONYMOUS.authenticated).toBe(false);
    expect(ANONYMOUS.username).toBeNull();
    expect(ANONYMOUS.is_staff).toBe(false);
  });

  it('sends the CSRF token on unsafe requests', async () => {
    document.cookie = 'csrftoken=tok-123';
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true, status: 200, json: async () => ({ authenticated: true }),
    });
    vi.stubGlobal('fetch', fetchMock);

    const { signIn } = await import('./session');
    await signIn('a', 'b');

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect((init.headers as Record<string, string>)['X-CSRFToken']).toBe('tok-123');
  });

  it('sends cookies so the session travels with the request', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true, status: 200, json: async () => ({ authenticated: false }),
    });
    vi.stubGlobal('fetch', fetchMock);

    const { getSession } = await import('./session');
    await getSession();

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(init.credentials).toBe('same-origin');
  });

  it('does not send a CSRF header on reads', async () => {
    document.cookie = 'csrftoken=tok-123';
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true, status: 200, json: async () => ({ authenticated: false }),
    });
    vi.stubGlobal('fetch', fetchMock);

    const { getSession } = await import('./session');
    await getSession();

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect((init.headers as Record<string, string>)['X-CSRFToken']).toBeUndefined();
  });

  it('never stores a credential client-side', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true, status: 200,
      json: async () => ({ authenticated: true, username: 'a', is_staff: false }),
    });
    vi.stubGlobal('fetch', fetchMock);

    const { signIn } = await import('./session');
    const identity = await signIn('a', 'pw');

    // The session is an HttpOnly cookie. Nothing secret reaches JavaScript.
    expect(Object.keys(identity)).toEqual(
      expect.arrayContaining(['authenticated', 'username', 'is_staff']),
    );
    expect(JSON.stringify(identity)).not.toContain('pw');
    expect(localStorage.getItem('token')).toBeNull();
  });
});
