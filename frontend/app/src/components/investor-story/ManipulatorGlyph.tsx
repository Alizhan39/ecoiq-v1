/**
 * ManipulatorGlyph — the one consistent visual representation of an EcoIQ
 * "manipulator" (an intelligence capability) used across every scene.
 *
 * Deliberately abstract/schematic, not photorealistic: a simple articulated
 * industrial arm — base, two jointed segments, a small tool head — in line
 * art. Never two glyphs touching or clasping (no handshake read), never
 * humanoid. Tint communicates which capability it stands in for; the label
 * beneath it names the capability explicitly so the metaphor never has to
 * carry meaning on its own.
 */
export default function ManipulatorGlyph({
  tint = 'var(--eiq-accent)',
  size = 56,
}: {
  tint?: string
  size?: number
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 56 56"
      fill="none"
      stroke={tint}
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {/* base plate */}
      <rect x="20" y="46" width="16" height="6" rx="1.5" />
      {/* first segment (vertical riser) */}
      <line x1="28" y1="46" x2="28" y2="34" />
      <circle cx="28" cy="34" r="2.4" fill={tint} stroke="none" />
      {/* second segment (angled) */}
      <line x1="28" y1="34" x2="16" y2="22" />
      <circle cx="16" cy="22" r="2.4" fill={tint} stroke="none" />
      {/* third segment to tool head */}
      <line x1="16" y1="22" x2="20" y2="10" />
      {/* tool head — small open pincer, never closed on anything */}
      <path d="M20 10 l-4 -3 M20 10 l4 -3" />
      <circle cx="20" cy="10" r="1.6" fill={tint} stroke="none" />
    </svg>
  )
}
