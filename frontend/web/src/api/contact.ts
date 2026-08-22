import { api, request } from './client';
import type {
  ContactAccepted, ContactForm, ContactSubmission,
} from '@/types/contact';

/**
 * Fetch the anti-abuse context the form needs.
 *
 * The token is issued per render, so it is fetched when the form mounts rather
 * than embedded in the shell — a token baked into a cached document would be
 * the same age for every visitor who received that copy.
 */
export function getContactForm(signal?: AbortSignal): Promise<ContactForm> {
  return api.get<ContactForm>('/contact/', signal);
}

export interface SubmitPayload extends ContactSubmission {
  /** Honeypot. Named `website` to look worth filling in; a human never sees it. */
  website: string;
  form_token: string;
  turnstile_token: string;
}

export function submitContact(payload: SubmitPayload): Promise<ContactAccepted> {
  return request<ContactAccepted>('/contact/', {
    method: 'POST',
    body: payload,
  });
}
