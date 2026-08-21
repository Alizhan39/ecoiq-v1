# React ↔ Django Auth Boundary

## The decision: no new authentication system

Django's session authentication already works, is already in the DRF
authenticator chain, already sets `Secure` cookies in production, and already
carries staff permissions.

A JWT layer would mean writing token issue, refresh, revocation and storage —
four new ways to be wrong — to replace something correct today. The SPA is
served from the **same origin** as the API, so the session cookie simply works.

**What was added: three endpoints, nothing else.**

| endpoint | why an SPA needs it |
|---|---|
| `GET /api/v2/session/` | a template knew from `request.user`; a static bundle has to ask — and this also sets the CSRF cookie |
| `POST /api/v2/session/sign-in/` | JSON in, JSON out, instead of an HTML redirect |
| `POST /api/v2/session/sign-out/` | same |

`/login/` and `/logout/` are **unchanged**. Django's `LoginView` still serves
staff tooling and the admin. This is an additional JSON surface over the same
`django.contrib.auth` primitives — not a second auth system.

## How a request is authenticated

```
Browser ──── same origin ────► /api/v2/…
   │  Cookie: sessionid (HttpOnly, Secure, SameSite)
   │  X-CSRFToken: <from csrftoken cookie>   ← unsafe methods only
   ▼
DRF authenticator chain
   1. MobileTokenAuthentication   (mobile app)
   2. APIKeyAuthentication        (B2B keys)
   3. SessionAuthentication       ← the SPA
```

The SPA sends `credentials: 'same-origin'` and reads the CSRF token from the
`csrftoken` cookie. It never sees the session key: `sessionid` is `HttpOnly`, and
that property is the reason not to move to a token in `localStorage`.

## CSRF: one line that is not obvious

DRF's `SessionAuthentication` enforces CSRF **only for requests it actually
authenticates**. An anonymous sign-in POST has no session user yet, so the check
never runs — and `@api_view` separately marks the view `csrf_exempt`.

The result is an **unprotected login endpoint**, which is *login-CSRF*: an
attacker forces a victim's browser to sign in as the **attacker**, and the
victim then works inside an account the attacker controls and can read.

Wrapping with `@csrf_protect` does not fix it. `functools.wraps` copies the
`csrf_exempt` attribute onto the new wrapper, and `CsrfViewMiddleware` skips any
view carrying it. So the flag is cleared directly:

```python
sign_in.csrf_exempt = False
sign_out.csrf_exempt = False
```

Found by a test that expected `403` and got `200`.

## Staff permissions

`is_staff` appears in the session payload as a **hint for rendering** — which
navigation to show. It is **not a permission**.

Every staff-only surface enforces its own check server-side, because anything
the client is told can be edited by the client. The league table's staff view is
decided by `request.user.is_staff` on the server; a client claiming `is_staff`
changes nothing.

## Deliberate response choices

| case | response | why |
|---|---|---|
| anonymous `GET /session/` | **200**, `authenticated: false` | the public product is anonymous by default; a 401 would make every first load look broken |
| bad password | **401**, generic message | identical to unknown-user, so this is not an enumeration oracle |
| sign out when already out | **200** | the caller asked for a state that is already true |
| `GET /sign-out/` | **405** | a sign-out reachable by GET can be fired by an `<img>` on any page |

Sign-in is throttled (`AnonRateThrottle`): an unthrottled JSON login endpoint is
a credential-stuffing target in a way a form behind a template is not.

## What is never returned

No token, no session key, no password echo. The payload is exactly
`{authenticated, username, is_staff}`, asserted by test.

## Coverage

`api/tests_v2_session.py` — 26 tests: anonymous access, sign in, sign out,
authenticated request, expired session, CSRF present/absent/wrong, staff
boundary, session-key rotation, and that the form login still works.

`frontend/web/src/api/session.test.ts` — 5 tests: CSRF header on unsafe methods
only, `credentials: same-origin`, and that nothing secret reaches JavaScript.
