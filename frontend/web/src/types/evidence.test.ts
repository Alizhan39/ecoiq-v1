import { describe, expect, it } from 'vitest';
import {
  coverageLabel,
  confidenceLabel,
  isPublished,
  isSignalClear,
  publishableScore,
  type CompanySummary,
} from './evidence';

const base: Pick<CompanySummary, 'score_status' | 'ecoiq_score'> = {
  score_status: 'PUBLISHED',
  ecoiq_score: 76.4,
};

describe('the score guard', () => {
  it('publishes a real score', () => {
    expect(isPublished(base)).toBe(true);
    expect(publishableScore(base)).toBe(76.4);
  });

  it('treats a genuine zero as a real, publishable score', () => {
    // The case client code gets wrong by treating 0 as falsy.
    const zero = { score_status: 'PUBLISHED', ecoiq_score: 0 } as const;

    expect(isPublished(zero)).toBe(true);
    expect(publishableScore(zero)).toBe(0);
  });

  it('withholds when the status is not PUBLISHED', () => {
    const withheld = {
      score_status: 'INSUFFICIENT_EVIDENCE',
      ecoiq_score: null,
    } as const;

    expect(isPublished(withheld)).toBe(false);
    expect(publishableScore(withheld)).toBeNull();
  });

  it('withholds even if a score is somehow present but unpublished', () => {
    // Defence in depth: status is authoritative, not the presence of a number.
    const inconsistent = {
      score_status: 'INSUFFICIENT_EVIDENCE',
      ecoiq_score: 71.4,
    } as const;

    expect(isPublished(inconsistent)).toBe(false);
    expect(publishableScore(inconsistent)).toBeNull();
  });

  it('handles PROVISIONAL as not-published', () => {
    const provisional = {
      score_status: 'PROVISIONAL',
      ecoiq_score: 55,
    } as const;

    expect(isPublished(provisional)).toBe(false);
  });

  it('returns null rather than a fallback number', () => {
    const withheld = {
      score_status: 'INSUFFICIENT_EVIDENCE',
      ecoiq_score: null,
    } as const;

    // A caller that ignores the null gets a compiler error, not a zero.
    expect(publishableScore(withheld)).not.toBe(0);
  });
});

describe('labels', () => {
  it('renders confidence as words, never a number', () => {
    expect(confidenceLabel('HIGH')).toBe('High');
    expect(confidenceLabel('INSUFFICIENT_EVIDENCE')).toBe('Insufficient evidence');
    expect(Number.isNaN(Number(confidenceLabel('LOW')))).toBe(true);
  });

  it('renders zero coverage as 0%, not as absent', () => {
    expect(coverageLabel(0)).toBe('0%');
  });
});

describe('harm signals', () => {
  const signal = (status: string) => ({
    id: 'x', label: 'X', status, penalty: 0, detail: '',
  });

  it('treats clear as clear', () => {
    expect(isSignalClear(signal('clear'))).toBe(true);
  });

  it('does not treat insufficient_evidence as clear', () => {
    // A check nobody ran is not a pass.
    expect(isSignalClear(signal('insufficient_evidence'))).toBe(false);
  });
});
