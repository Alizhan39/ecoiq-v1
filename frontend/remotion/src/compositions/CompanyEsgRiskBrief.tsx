import React from 'react';
import { AbsoluteFill, Sequence } from 'remotion';
import { EIQ, FONT } from '../lib/theme';
import { Backdrop, Logo, Eyebrow, Counter, Rise, Disclaimer } from '../components/Shared';

export type CompanyBriefProps = {
  company: string;
  sector: string;
  ecoiqScore: number;
  moralLabel: string;
  risks: { label: string; level: 'Low' | 'Medium' | 'High' }[];
};

const RISK_COLOR: Record<string, string> = { Low: EIQ.green, Medium: EIQ.warn, High: EIQ.danger };

export const companyDefaults: CompanyBriefProps = {
  company: 'Meridian Industrial Holdings',
  sector: 'Heavy Industry',
  ecoiqScore: 84.2,
  moralLabel: 'Regenerative Leader',
  risks: [
    { label: 'Climate transition', level: 'Medium' },
    { label: 'Governance & disclosure', level: 'Low' },
    { label: 'Fasad / harm exposure', level: 'Low' },
  ],
};

export const CompanyEsgRiskBrief: React.FC<CompanyBriefProps> = (p) => (
  <AbsoluteFill style={{ fontFamily: FONT, color: EIQ.text }}>
    <Backdrop accent={EIQ.blue} />
    <AbsoluteFill style={{ padding: 80, justifyContent: 'center' }}>
      <Sequence from={0}>
        <Rise from={6}><Logo /></Rise>
        <Rise from={16} style={{ marginTop: 40 }}>
          <Eyebrow color={EIQ.blue}>Company ESG Risk Brief</Eyebrow>
        </Rise>
        <Rise from={24}>
          <div style={{ fontSize: 72, fontWeight: 900, letterSpacing: '-0.03em', color: '#fff', lineHeight: 1.05 }}>
            {p.company}
          </div>
          <div style={{ fontSize: 28, color: EIQ.muted, marginTop: 10 }}>{p.sector}</div>
        </Rise>
      </Sequence>

      <Sequence from={40}>
        <Rise from={40} style={{ display: 'flex', alignItems: 'center', gap: 40, marginTop: 50 }}>
          <div style={{ fontSize: 84, fontWeight: 300, color: EIQ.green }}>
            <Counter to={p.ecoiqScore} decimals={1} color={EIQ.green} delay={40} />
          </div>
          <div>
            <div style={{ fontSize: 18, color: EIQ.faint, letterSpacing: '0.1em', textTransform: 'uppercase' }}>EcoIQ Score</div>
            <div style={{ fontSize: 30, color: EIQ.green, fontWeight: 700 }}>▲ {p.moralLabel}</div>
          </div>
        </Rise>
      </Sequence>

      <Sequence from={66}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14, marginTop: 50, maxWidth: 760 }}>
          {p.risks.map((r, i) => (
            <Rise key={i} from={66 + i * 10}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: EIQ.bg2, border: `1px solid ${EIQ.border}`, borderRadius: 12, padding: '18px 24px' }}>
                <span style={{ fontSize: 26, color: EIQ.text }}>{r.label}</span>
                <span style={{ fontSize: 18, fontWeight: 700, color: RISK_COLOR[r.level], border: `1px solid ${RISK_COLOR[r.level]}55`, background: `${RISK_COLOR[r.level]}18`, padding: '6px 16px', borderRadius: 20, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  {r.level}
                </span>
              </div>
            </Rise>
          ))}
        </div>
      </Sequence>

      <Sequence from={130}>
        <Rise from={130} style={{ marginTop: 56 }}>
          <div style={{ fontSize: 28, color: EIQ.blue, fontWeight: 700 }}>Request the full Investor Readiness Report → ecoiq.uk</div>
        </Rise>
      </Sequence>
    </AbsoluteFill>
    <Disclaimer>Indicative, AI-assisted. Analyst review required before any decision.</Disclaimer>
  </AbsoluteFill>
);
