import React from 'react';
import { AbsoluteFill, Sequence } from 'remotion';
import { EIQ, FONT } from '../lib/theme';
import { Backdrop, Logo, Eyebrow, Counter, Rise, Disclaimer } from '../components/Shared';

export type CountryBriefProps = {
  country: string;
  headline: string;
  ecoiqScore: number;
  maqasidScore: number;
  kpis: { label: string; value: string }[];
};

export const countryDefaults: CountryBriefProps = {
  country: 'Kazakhstan',
  headline: 'Country Transition Intelligence',
  ecoiqScore: 84.2,
  maqasidScore: 92,
  kpis: [
    { label: 'Coal share of heating', value: 'High' },
    { label: 'Transition readiness', value: 'Improving' },
    { label: 'Priority sectors', value: '4' },
  ],
};

export const CountryTransitionBrief: React.FC<CountryBriefProps> = (p) => (
  <AbsoluteFill style={{ fontFamily: FONT, color: EIQ.text }}>
    <Backdrop accent={EIQ.green} />
    <AbsoluteFill style={{ padding: 80, justifyContent: 'center' }}>
      <Sequence from={0}>
        <Rise from={6}>
          <Logo />
        </Rise>
        <Rise from={16} style={{ marginTop: 40 }}>
          <Eyebrow color={EIQ.gold}>Country Transition Brief</Eyebrow>
        </Rise>
        <Rise from={24}>
          <div style={{ fontSize: 92, fontWeight: 900, letterSpacing: '-0.04em', color: '#fff', lineHeight: 1.05 }}>
            {p.country}
          </div>
          <div style={{ fontSize: 30, color: EIQ.muted, marginTop: 10 }}>{p.headline}</div>
        </Rise>
      </Sequence>

      <Sequence from={40}>
        <Rise from={40} style={{ display: 'flex', gap: 64, marginTop: 56 }}>
          <div>
            <div style={{ fontSize: 18, color: EIQ.faint, letterSpacing: '0.1em', textTransform: 'uppercase' }}>EcoIQ Score</div>
            <div style={{ fontSize: 84, fontWeight: 300 }}>
              <Counter to={p.ecoiqScore} decimals={1} color={EIQ.green} delay={40} />
            </div>
          </div>
          <div>
            <div style={{ fontSize: 18, color: EIQ.faint, letterSpacing: '0.1em', textTransform: 'uppercase' }}>Maqasid Score</div>
            <div style={{ fontSize: 84, fontWeight: 300 }}>
              <Counter to={p.maqasidScore} color={EIQ.gold} delay={48} />
            </div>
          </div>
        </Rise>
      </Sequence>

      <Sequence from={70}>
        <div style={{ display: 'flex', gap: 18, marginTop: 56, flexWrap: 'wrap' }}>
          {p.kpis.map((k, i) => (
            <Rise key={i} from={70 + i * 10}>
              <div style={{ background: EIQ.bg2, border: `1px solid ${EIQ.border}`, borderRadius: 14, padding: '20px 26px', minWidth: 260 }}>
                <div style={{ fontSize: 18, color: EIQ.faint }}>{k.label}</div>
                <div style={{ fontSize: 34, fontWeight: 700, color: '#fff', marginTop: 6 }}>{k.value}</div>
              </div>
            </Rise>
          ))}
        </div>
      </Sequence>

      <Sequence from={130}>
        <Rise from={130} style={{ marginTop: 64 }}>
          <div style={{ fontSize: 30, color: EIQ.green, fontWeight: 700 }}>ecoiq.uk · Climate Intelligence + Real-World Impact</div>
        </Rise>
      </Sequence>
    </AbsoluteFill>
    <Disclaimer>Indicative, AI-assisted. Not investment advice.</Disclaimer>
  </AbsoluteFill>
);
