/** The contact enquiry flow. Mirrors api/v2_contact.py. */

export interface ContactForm {
  /** Signed render timestamp. A submission that arrives implausibly fast, or
   *  with a forged or absent token, is detectable. Opaque to the client. */
  form_token: string;
  /** Empty when Turnstile is not configured for this environment. The widget
   *  is then not rendered, and the server does not require a token. */
  turnstile_site_key: string;
}

export interface ContactSubmission {
  name: string;
  email: string;
  subject: string;
  company: string;
  message: string;
}

export interface ContactAccepted {
  status: 'received';
  detail: string;
}

/** Field-level messages, keyed by field name. */
export type ContactErrors = Partial<
  Record<keyof ContactSubmission | 'detail', string>
>;
