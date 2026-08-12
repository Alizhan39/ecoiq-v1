// EcoIQ institutional palette + helpers shared by all video compositions.
export const EIQ = {
  bg: '#070b0f',
  bg2: '#0d1117',
  panel: '#161b22',
  border: 'rgba(255,255,255,0.08)',
  text: '#e2e8f0',
  muted: '#94a3b8',
  faint: '#64748b',
  green: '#00e89a',
  gold: '#c9a84c',
  blue: '#58a6ff',
  purple: '#a855f7',
  danger: '#e63946',
  warn: '#f4a261',
};

export const FONT =
  '-apple-system, BlinkMacSystemFont, "Segoe UI", Inter, Roboto, sans-serif';
export const MONO = '"SF Mono", "Fira Code", ui-monospace, monospace';

// Smooth 0→1 progress for a frame window.
export const ramp = (
  frame: number,
  start: number,
  end: number,
  interpolate: (i: number, r: number[], o: number[], opts?: object) => number,
) =>
  interpolate(frame, [start, end], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
