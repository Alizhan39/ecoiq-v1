import React from 'react';
import { AbsoluteFill, Sequence } from 'remotion';
import { EIQ, FONT } from '../lib/theme';
import { Backdrop, Logo, Eyebrow, Counter, Rise, Disclaimer } from '../components/Shared';

export type ToursProps = {
  headline: string;
  homesUpgraded: number;
  dailyBenefits: string[];
};

export const toursDefaults: ToursProps = {
  headline: 'Eco Tours with Daily Impact',
  homesUpgraded: 10,
  dailyBenefits: [
    'A family breathes cleaner air',
    'Air pollution is reduced',
    'Coal consumption decreases',
    'Benefit for future generations',
  ],
};

export const KhalifaToursImpactExplainer: React.FC<ToursProps> = (p) => (
  <AbsoluteFill style={{ fontFamily: FONT, color: EIQ.text }}>
    <Backdrop accent={EIQ.gold} />
    <AbsoluteFill style={{ padding: 80, justifyContent: 'center' }}>
      <Sequence from={0}>
        <Rise from={6}><Logo /></Rise>
        <Rise from={16} style={{ marginTop: 40 }}>
          <Eyebrow color={EIQ.gold}>Khalifa Tours · Impact Explainer</Eyebrow>
        </Rise>
        <Rise from={24}>
          <div style={{ fontSize: 78, fontWeight: 900, letterSpacing: '-0.03em', color: '#fff', lineHeight: 1.06, maxWidth: 1200 }}>
            {p.headline}
          </div>
          <div style={{ fontSize: 30, color: EIQ.muted, marginTop: 14 }}>
            Travel to Kazakhstan. Help families move from coal heating to cleaner homes.
          </div>
        </Rise>
      </Sequence>

      <Sequence from={48}>
        <Rise from={48} style={{ display: 'flex', alignItems: 'baseline', gap: 22, marginTop: 50 }}>
          <div style={{ fontSize: 110, fontWeight: 900, color: EIQ.gold }}>
            <Counter to={p.homesUpgraded} color={EIQ.gold} delay={48} />
          </div>
          <div style={{ fontSize: 30, color: EIQ.muted }}>homes upgraded — benefit every day</div>
        </Rise>
      </Sequence>

      <Sequence from={72}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginTop: 44 }}>
          {p.dailyBenefits.map((b, i) => (
            <Rise key={i} from={72 + i * 10} style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
              <span style={{ color: EIQ.green, fontSize: 30 }}>✦</span>
              <span style={{ fontSize: 30, color: EIQ.text }}>{b}</span>
            </Rise>
          ))}
        </div>
      </Sequence>

      <Sequence from={140}>
        <Rise from={140} style={{ marginTop: 56 }}>
          <div style={{ fontSize: 40, fontWeight: 800, color: '#fff' }}>
            Travel today. <span style={{ color: EIQ.gold }}>Benefit every day.</span>
          </div>
          <div style={{ fontSize: 26, color: EIQ.green, marginTop: 10 }}>ecoiq.uk/heating</div>
        </Rise>
      </Sequence>
    </AbsoluteFill>
    <Disclaimer>Impact measured per home and reported through EcoIQ. Indicative.</Disclaimer>
  </AbsoluteFill>
);
