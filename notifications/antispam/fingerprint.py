"""
Normalisation and fingerprinting for duplicate suppression.

The fingerprint never contains the message itself — only a truncated HMAC of
the normalised parts, keyed with SECRET_KEY. That makes it useless to anyone
reading the database and safe to log.
"""
import hashlib
import hmac
import re
import unicodedata

from django.conf import settings

_WS = re.compile(r'\s+')
_PUNCT = re.compile(r'[^\w\s]', re.UNICODE)


def _key():
    return (getattr(settings, 'SECRET_KEY', '') or '').encode('utf-8')


def normalise_text(value, *, strip_punctuation=True):
    """Casefold, strip accents, collapse whitespace; optionally drop punctuation."""
    if not value:
        return ''
    text = unicodedata.normalize('NFKD', str(value))
    text = ''.join(c for c in text if not unicodedata.combining(c))
    text = text.casefold()
    if strip_punctuation:
        text = _PUNCT.sub(' ', text)
    return _WS.sub(' ', text).strip()


def normalise_email(value):
    """
    Lowercase, trim, and collapse the common alias tricks a single abuser uses
    to look like many people: gmail dots and +tags.
    """
    email = (value or '').strip().casefold()
    if '@' not in email:
        return email
    local, _, domain = email.rpartition('@')
    local = local.split('+', 1)[0]
    if domain in ('gmail.com', 'googlemail.com'):
        local = local.replace('.', '')
        domain = 'gmail.com'
    return f'{local}@{domain}'


def email_domain(value):
    email = normalise_email(value)
    return email.rpartition('@')[2] if '@' in email else ''


def _digest(*parts):
    payload = '\x1f'.join(parts).encode('utf-8')
    return hmac.new(_key(), payload, hashlib.sha256).hexdigest()[:32]


def submission_fingerprint(*, email='', name='', subject='', message='', form=''):
    """
    Stable identifier for "the same submission again".

    Deliberately excludes the raw message: only its normalised digest
    contributes, so the fingerprint can be stored and logged without carrying
    the personal content of an enquiry.
    """
    return _digest(
        form or '',
        normalise_email(email),
        normalise_text(name),
        normalise_text(subject),
        _digest(normalise_text(message)),
    )


def content_fingerprint(message, *, form=''):
    """Fingerprint of the message body alone — catches one text blasted from many addresses."""
    return _digest('content', form or '', _digest(normalise_text(message)))


def hashed_ip(ip):
    """
    Keyed, truncated hash of an IP for rate-limit keys and logs.

    Raw addresses are never stored or logged: the hash is enough to count
    repeat offenders and cannot be reversed to an address without SECRET_KEY.
    """
    if not ip:
        return ''
    return _digest('ip', str(ip))[:16]
