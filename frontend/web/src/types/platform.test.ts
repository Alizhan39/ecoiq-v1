import { describe, expect, it } from 'vitest';
import { counterDisplay, isEvaluated, NOT_MEASURED } from './platform';

const counter = (value: number | null) => ({
  key: 'k', label: 'L', value, derivation: 'd', is_proof: false,
});

describe('counter display', () => {
  it('renders an absent figure as an em dash', () => {
    // Never 0: "0 verified projects" reads as a failed verification.
    expect(counterDisplay(counter(null))).toBe('—');
  });

  it('renders a real zero as zero', () => {
    expect(counterDisplay(counter(0))).toBe('0');
  });

  it('does not confuse the two', () => {
    expect(counterDisplay(counter(null))).not.toBe(counterDisplay(counter(0)));
  });

  it('formats large numbers readably', () => {
    expect(counterDisplay(counter(1234))).toBe('1,234');
  });
});

describe('module evaluation', () => {
  const mod = (evaluation: string) => ({
    key: 'k', name: 'N', kind: 'AI_AGENT', status: 'BETA' as const,
    evaluation, basis: 'b',
  });

  it('recognises an unevaluated module', () => {
    expect(isEvaluated(mod(NOT_MEASURED))).toBe(false);
  });

  it('never renders NOT YET MEASURED as a number', () => {
    expect(Number.isNaN(Number(NOT_MEASURED))).toBe(true);
  });
});
