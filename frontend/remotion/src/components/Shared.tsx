import React from 'react';
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from 'remotion';
import { EIQ, FONT, MONO } from '../lib/theme';

// Dark institutional backdrop: gradient + faint data grid + soft accent glow.
export const Backdrop: React.FC<{ accent?: string }> = ({ accent = EIQ.green }) => (
  <AbsoluteFill style={{ background: `linear-gradient(160deg, ${EIQ.bg} 0%, ${EIQ.bg2} 60%, ${EIQ.bg} 100%)` }}>
    <AbsoluteFill
      style={{
        backgroundImage:
          'linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px)',
        backgroundSize: '64px 64px',
        maskImage: 'radial-gradient(ellipse 80% 70% at 70% 45%, #000 30%, transparent 85%)',
      }}
    />
    <AbsoluteFill
      style={{ background: `radial-gradient(circle at 72% 40%, ${accent}22, transparent 60%)` }}
    />
  </AbsoluteFill>
);

export const Logo: React.FC = () => (
  <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
    <svg width="40" height="40" viewBox="0 0 40 40" fill="none">
      <rect width="40" height="40" rx="9" fill="#070b0f" />
      <polygon points="20,4 33.9,12 33.9,28 20,36 6.1,28 6.1,12" stroke={EIQ.green} strokeWidth="2" strokeLinejoin="round" />
      <polygon points="20,11 27.8,24.5 12.2,24.5" fill="rgba(0,232,154,0.08)" stroke={EIQ.green} strokeWidth="1.4" strokeLinejoin="round" />
      <circle cx="20" cy="20" r="2.8" fill={EIQ.green} />
    </svg>
    <span style={{ fontFamily: FONT, fontWeight: 800, fontSize: 28, color: '#fff', letterSpacing: '-0.02em' }}>
      Eco<span style={{ color: EIQ.green }}>IQ</span>
    </span>
  </div>
);

export const Eyebrow: React.FC<{ children: React.ReactNode; color?: string }> = ({ children, color = EIQ.gold }) => (
  <div
    style={{
      fontFamily: MONO, fontSize: 22, fontWeight: 700, letterSpacing: '0.18em', textTransform: 'uppercase',
      color, marginBottom: 22,
    }}
  >
    {children}
  </div>
);

// Animated number counter.
export const Counter: React.FC<{ to: number; suffix?: string; color?: string; decimals?: number; delay?: number }> = ({
  to, suffix = '', color = EIQ.green, decimals = 0, delay = 0,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = spring({ frame: frame - delay, fps, config: { damping: 200 } });
  const val = (p * to).toFixed(decimals);
  return (
    <span style={{ fontFamily: FONT, fontWeight: 800, color, fontVariantNumeric: 'tabular-nums' }}>
      {val}{suffix}
    </span>
  );
};

// Fade + rise on entry, keyed to a start frame.
export const Rise: React.FC<{ from: number; children: React.ReactNode; style?: React.CSSProperties }> = ({ from, children, style }) => {
  const frame = useCurrentFrame();
  const o = interpolate(frame, [from, from + 16], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const y = interpolate(frame, [from, from + 16], [22, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  return <div style={{ opacity: o, transform: `translateY(${y}px)`, ...style }}>{children}</div>;
};

export const Disclaimer: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div style={{ position: 'absolute', bottom: 40, left: 80, fontFamily: MONO, fontSize: 16, color: EIQ.faint }}>
    {children}
  </div>
);
