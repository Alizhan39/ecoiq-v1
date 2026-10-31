import { describe, expect, it } from 'vitest';
import * as demo from './demoData';
import {
  paybackYears, percent, poundsToK, variancePercent, years,
} from './economics';

/**
 * The dataset's guard rails.
 *
 * These are not unit tests of arithmetic. They are the things that must stay
 * true about a fictitious dataset shown to a buyer: that it is labelled, that
 * its headline is the sum of its rows, and that the same intervention costs
 * the same in the two places it appears.
 */

/** Everything that looks like a Quantity, anywhere in the module. */
function everyQuantity(value: unknown, found: Record<string, unknown>[] = []) {
  if (Array.isArray(value)) {
    value.forEach((entry) => everyQuantity(entry, found));
    return found;
  }
  if (value && typeof value === 'object') {
    const record = value as Record<string, unknown>;
    if ('value' in record && 'unit' in record) found.push(record);
    Object.values(record).forEach((entry) => everyQuantity(entry, found));
  }
  return found;
}

describe('demonstration labelling', () => {
  it('says the dataset is fictitious in plain words', () => {
    expect(demo.DEMONSTRATION_NOTICE).toMatch(/fictitious/i);
    expect(demo.DEMONSTRATION_NOTICE).toMatch(/demonstration/i);
  });

  it('denies that anything shown is a client outcome', () => {
    // The notice used to add "EcoIQ has delivered no public-sector
    // engagement". That is true, and on a landing page it reads as a
    // confession rather than as a label on the data. What has to survive is
    // the protective half: nothing here describes a real client. That is a
    // statement about the dataset, and it is the one a reader could be
    // misled without.
    expect(demo.DEMONSTRATION_NOTICE)
      .toMatch(/no real organisation, asset, saving or client outcome/i);
  });

  it('carries a short badge for use beside a figure', () => {
    expect(demo.DEMONSTRATION_BADGE).toMatch(/demonstration data/i);
  });
});

describe('every quantity is marked illustrative', () => {
  it('finds a real number of quantities to check', () => {
    // Guards the guard: a walk that finds nothing passes trivially.
    expect(everyQuantity(demo).length).toBeGreaterThan(50);
  });

  it('leaves none of them unmarked or marked as measured', () => {
    const wrong = everyQuantity(demo).filter((q) => q.basis !== 'illustrative');

    expect(wrong).toEqual([]);
  });
});

describe('the estate headline is the sum of its rows', () => {
  it('flags seventeen assets', () => {
    expect(demo.FLAGGED_ASSETS).toHaveLength(17);
    expect(demo.portfolioTotals().assetCount).toBe(17);
  });

  it('totals £740,000 of annual saving', () => {
    expect(demo.portfolioTotals().annualSaving).toBe(740_000);
  });

  it('flags fewer assets than the estate has buildings', () => {
    expect(demo.portfolioTotals().assetCount)
      .toBeLessThan(demo.ESTATE.buildings.value);
  });

  it('gives every asset a unique id', () => {
    const ids = demo.FLAGGED_ASSETS.map((asset) => asset.id);

    expect(new Set(ids).size).toBe(ids.length);
  });

  it('names no identifiable building', () => {
    // Role labels only — an invented school name is indistinguishable from a
    // real one, and there is a real school behind almost any plausible name.
    for (const asset of demo.FLAGGED_ASSETS) {
      expect(asset.name).not.toMatch(/\b(primary|academy|trust|NHS|London)\b/i);
    }
  });
});

describe('the drill-down agrees with the portfolio', () => {
  it('costs the boiler upgrade the same in both places', () => {
    const asset = demo.assetById('leisure-centre')!;
    const option = demo.LEISURE_CENTRE_INTERVENTIONS
      .find((entry) => entry.id === 'boiler-upgrade')!;

    expect(option.capex.value).toBe(asset.capex.value);
    expect(option.annualSaving.value).toBe(asset.annualSaving.value);
    expect(option.emissionsReduction.value).toBe(asset.emissionsReduction.value);
  });

  it('forecasts the MRV outcome from that same intervention', () => {
    const asset = demo.assetById('leisure-centre')!;

    expect(demo.MRV_OUTCOME.forecastAnnualSaving.value)
      .toBe(asset.annualSaving.value);
  });

  it('returns null for an unknown asset rather than throwing', () => {
    expect(demo.assetById('no-such-asset')).toBeNull();
  });
});

describe('derived figures', () => {
  it('computes the paybacks the page displays', () => {
    const cases = [
      ['school-a', '1.4 years'],
      ['leisure-centre', '1.4 years'],
      ['council-office', '1.1 years'],
    ] as const;

    for (const [id, expected] of cases) {
      const asset = demo.assetById(id)!;
      expect(years(paybackYears(asset.capex.value, asset.annualSaving.value)))
        .toBe(expected);
    }
  });

  it('computes the intervention paybacks', () => {
    const displayed = demo.LEISURE_CENTRE_INTERVENTIONS.map((option) =>
      years(paybackYears(option.capex.value, option.annualSaving.value)));

    expect(displayed).toEqual(['0.7 years', '1.4 years', '3.5 years']);
  });

  it('computes the MRV variance rather than storing it', () => {
    const variance = variancePercent(
      demo.MRV_OUTCOME.verifiedAnnualSaving.value,
      demo.MRV_OUTCOME.forecastAnnualSaving.value,
    );

    expect(percent(variance)).toBe('−3.3%');
    // The verified saving is BELOW forecast, and the sign has to say so.
    expect(variance!).toBeLessThan(0);
  });

  it('has no payback for a saving that cannot produce one', () => {
    expect(paybackYears(1000, 0)).toBeNull();
    expect(years(null)).toBe('—');
  });

  it('formats money without inventing precision', () => {
    expect(poundsToK(42_000)).toBe('£42k');
  });
});

describe('evidence', () => {
  it('states source, date, confidence, methodology and status for each item', () => {
    for (const item of demo.LEISURE_CENTRE_EVIDENCE) {
      expect(item.source).toBeTruthy();
      expect(item.date).toMatch(/^\d{4}-\d{2}-\d{2}$/);
      expect(item.confidence).toBeTruthy();
      expect(item.methodology).toBeTruthy();
      expect(item.status).toBeTruthy();
    }
  });

  it('does not show every item as strong', () => {
    // A demonstration evidence panel where everything is verified teaches a
    // buyer the opposite of what this product does.
    const weak = demo.LEISURE_CENTRE_EVIDENCE
      .filter((item) => item.confidence !== 'High' || item.status !== 'Verified');

    expect(weak.length).toBeGreaterThan(0);
  });

  it('covers the seven evidence types the recommendation rests on', () => {
    expect(demo.LEISURE_CENTRE_EVIDENCE).toHaveLength(7);
  });
});

describe('the human gate', () => {
  it('offers approve, reject and request further analysis', () => {
    expect(demo.APPROVAL_ACTIONS.map((action) => action.label))
      .toEqual(['Approve', 'Reject', 'Request further analysis']);
  });

  it('leaves the recommendation awaiting a person', () => {
    expect(demo.LEISURE_CENTRE_RECOMMENDATION.status)
      .toMatch(/needs human approval/i);
  });
});

describe('the MRV loop', () => {
  it('runs baseline through to verified outcome', () => {
    expect(demo.MRV_STAGES.map((stage) => stage.key)).toEqual([
      'baseline', 'intervention', 'measurement', 'normalisation', 'actual',
      'variance', 'verified',
    ]);
  });

  it('reports the verified saving below the forecast, and says so', () => {
    expect(demo.MRV_OUTCOME.verifiedAnnualSaving.value)
      .toBeLessThan(demo.MRV_OUTCOME.forecastAnnualSaving.value);
    expect(demo.MRV_OUTCOME.caveat).toMatch(/optimistic/i);
  });

  it('states no variance figure in the prose beside the computed one', () => {
    // It said "here it was 3.3% optimistic" — the variance, restated by hand,
    // in the one module whose whole argument is that derived numbers are
    // derived. Change the verified saving and the sentence would have gone on
    // claiming 3.3% next to a computed figure saying something else.
    expect(demo.MRV_OUTCOME.caveat).not.toMatch(/\d/);
  });
});
