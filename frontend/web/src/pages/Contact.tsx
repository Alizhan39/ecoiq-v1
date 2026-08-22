import { useCallback, useEffect, useRef, useState } from 'react';
import { ApiError } from '@/api/client';
import { getContactForm, submitContact } from '@/api/contact';
import type { ContactErrors, ContactForm } from '@/types/contact';

/**
 * Contact.
 *
 * The real enquiry flow, not a mailto link dressed as a form. It posts to
 * /api/v2/contact/, which runs the same abuse screening as the server-rendered
 * form it replaces — honeypot, signed render token, Turnstile, rate limit —
 * before anything is created or emailed.
 *
 * NOTHING IS INVENTED HERE
 * ------------------------
 * No offices, no regional phone numbers, no support hours, no customer count.
 * The founder's address is the real one and is the only contact detail EcoIQ
 * actually has.
 */

const TOPICS = [
  'Assessment enquiry',
  'Pilot or engagement',
  'Partnership',
  'Press',
  'Something else',
] as const;

const EMPTY = {
  name: '', email: '', subject: TOPICS[0] as string, company: '', message: '',
};

type Status = 'editing' | 'sending' | 'sent';

export default function Contact() {
  const [values, setValues] = useState(EMPTY);
  const [errors, setErrors] = useState<ContactErrors>({});
  const [status, setStatus] = useState<Status>('editing');
  const [form, setForm] = useState<ContactForm | null>(null);
  const turnstileToken = useRef('');

  useEffect(() => {
    const controller = new AbortController();
    getContactForm(controller.signal)
      .then(setForm)
      // A failure here is not fatal: the form still submits, and the server
      // decides what to do with a missing token. Blocking the whole page on it
      // would turn a spam-control hiccup into "EcoIQ has no contact page".
      .catch(() => undefined);
    return () => controller.abort();
  }, []);

  const set = useCallback((field: keyof typeof EMPTY, value: string) => {
    setValues((current) => ({ ...current, [field]: value }));
    setErrors((current) => ({ ...current, [field]: undefined }));
  }, []);

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (status === 'sending') return;
    setStatus('sending');
    setErrors({});

    try {
      await submitContact({
        ...values,
        website: '',                       // honeypot, never filled by a human
        form_token: form?.form_token ?? '',
        turnstile_token: turnstileToken.current,
      });
      setStatus('sent');
    } catch (error) {
      setStatus('editing');
      setErrors(errorsFrom(error));
    }
  }

  if (status === 'sent') {
    return (
      <div className="prose">
        <h1>Message received</h1>
        <p>
          Thank you — we&rsquo;ll reply to {values.email} within one business
          day.
        </p>
      </div>
    );
  }

  return (
    <div className="prose contact">
      <h1>Contact</h1>
      <p>
        About an assessment, a pilot, or a partnership. Enquiries reach the team
        directly — there is no ticket queue in between.
      </p>

      <form onSubmit={onSubmit} noValidate>
        {errors.detail ? (
          <p className="state state--error" role="alert">{errors.detail}</p>
        ) : null}

        <Field
          id="name" label="Name" value={values.name}
          error={errors.name} onChange={(v) => set('name', v)} required
        />
        <Field
          id="email" label="Email" type="email" value={values.email}
          error={errors.email} onChange={(v) => set('email', v)} required
        />
        <Field
          id="company" label="Organisation" value={values.company}
          error={errors.company} onChange={(v) => set('company', v)}
        />

        <div className="field">
          <label className="field__label" htmlFor="subject">Topic</label>
          <select
            id="subject" className="field__input" value={values.subject}
            onChange={(event) => set('subject', event.target.value)}
          >
            {TOPICS.map((topic) => (
              <option key={topic} value={topic}>{topic}</option>
            ))}
          </select>
        </div>

        <div className="field">
          <label className="field__label" htmlFor="message">Message</label>
          <textarea
            id="message" className="field__input" rows={7}
            value={values.message} required minLength={20}
            aria-describedby={errors.message ? 'message-error' : 'message-hint'}
            aria-invalid={errors.message ? true : undefined}
            onChange={(event) => set('message', event.target.value)}
          />
          {errors.message ? (
            <p className="field__error" id="message-error" role="alert">
              {errors.message}
            </p>
          ) : (
            <p className="field__hint" id="message-hint">
              At least 20 characters.
            </p>
          )}
        </div>

        {/* Honeypot. Hidden from sight and from assistive technology, and
            excluded from tab order — a human cannot reach it, so anything in
            it came from something automated. */}
        <div className="visually-hidden" aria-hidden="true">
          <label htmlFor="website">Website</label>
          <input id="website" name="website" tabIndex={-1} autoComplete="off" />
        </div>

        <Turnstile
          siteKey={form?.turnstile_site_key ?? ''}
          onToken={(token) => { turnstileToken.current = token; }}
        />

        <button type="submit" className="cta" disabled={status === 'sending'}>
          {status === 'sending' ? 'Sending…' : 'Send message'}
        </button>
      </form>

      <section aria-labelledby="direct">
        <h2 id="direct">Direct</h2>
        <p>
          <a href="mailto:alizhan@ecoiq.uk">alizhan@ecoiq.uk</a>
        </p>
        <p className="state__detail">
          EcoIQ was founded in London. It is a small team, so a direct email
          reaches the same people this form does.
        </p>
      </section>
    </div>
  );
}


function Field({
  id, label, value, onChange, error, hint, type = 'text', required = false,
}: {
  id: keyof typeof EMPTY & string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  error?: string | undefined;
  hint?: string;
  type?: string;
  required?: boolean;
}) {
  const describedBy = error ? `${id}-error` : hint ? `${id}-hint` : undefined;
  return (
    <div className="field">
      <label className="field__label" htmlFor={id}>
        {label}
        {required ? null : <span className="field__optional"> (optional)</span>}
      </label>
      <input
        id={id}
        className="field__input"
        type={type}
        value={value}
        required={required}
        aria-invalid={error ? true : undefined}
        {...(describedBy ? { 'aria-describedby': describedBy } : {})}
        onChange={(event) => onChange(event.target.value)}
      />
      {error ? (
        <p className="field__error" id={`${id}-error`} role="alert">{error}</p>
      ) : hint ? (
        <p className="field__hint" id={`${id}-hint`}>{hint}</p>
      ) : null}
    </div>
  );
}


/**
 * Cloudflare Turnstile, rendered only when a site key is configured.
 *
 * Explicit rendering rather than the auto-scan, so React owns the container's
 * lifecycle. If the script fails to load the token stays empty and the server
 * decides what to do — which is the same position the form is in when
 * Turnstile is not configured at all.
 */
declare global {
  interface Window {
    turnstile?: {
      render: (
        element: HTMLElement,
        options: { sitekey: string; callback: (token: string) => void },
      ) => void;
    };
  }
}

const TURNSTILE_SRC = 'https://challenges.cloudflare.com/turnstile/v0/api.js';

function Turnstile({
  siteKey, onToken,
}: { siteKey: string; onToken: (token: string) => void }) {
  const container = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!siteKey || !container.current) return undefined;
    const element = container.current;

    const render = () => {
      window.turnstile?.render(element, { sitekey: siteKey, callback: onToken });
    };

    if (window.turnstile) {
      render();
      return undefined;
    }

    const existing = document.querySelector<HTMLScriptElement>(
      `script[src="${TURNSTILE_SRC}"]`);
    const script = existing ?? document.createElement('script');
    script.src = TURNSTILE_SRC;
    script.async = true;
    script.addEventListener('load', render);
    if (!existing) document.head.appendChild(script);

    return () => script.removeEventListener('load', render);
  }, [siteKey, onToken]);

  if (!siteKey) return null;
  return <div className="field" ref={container} />;
}


/**
 * Turn a failed request into field messages.
 *
 * A 429 is given its own wording. "Something went wrong" for a rate limit
 * sends the sender straight back to resubmitting, which is the one thing that
 * makes it worse.
 */
function errorsFrom(error: unknown): ContactErrors {
  if (!(error instanceof ApiError)) {
    return { detail: 'Could not reach the server. Please try again.' };
  }
  if (error.status === 429) {
    return {
      detail: 'Too many submissions from this connection. Please try again '
        + 'later, or email alizhan@ecoiq.uk directly.',
    };
  }
  const body = error.body;
  if (body && typeof body === 'object' && 'errors' in body) {
    const fields = (body as { errors: unknown }).errors;
    if (fields && typeof fields === 'object') return fields as ContactErrors;
  }
  return { detail: 'Your message could not be sent. Please try again.' };
}
