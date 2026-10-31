---
name: ecoiq-brand
description: EcoIQ's own brand rules — logo, colour, typography, voice and tone, how Khalifah AI output is presented, terminology policy for Islamic concepts, and claims discipline. Use when producing anything a reader sees as coming from EcoIQ: marketing pages, decks, PDFs, social assets, video, email, or UI copy. Not for internal-only tooling output, and not a substitute for design/tokens.ts when writing app CSS.
---

# EcoIQ brand

Structure follows Anthropic's `brand-guidelines` skill pattern (colours →
typography → application → technical detail). **Every value below is read
from this repository.** Nothing is invented; gaps are listed at the bottom as
decisions required rather than filled in with a plausible guess.

## Colour — source of truth

`frontend/app/src/design/tokens.ts` and `design/system.css`. Do not restate
hexes from memory; read the file. Current palette:

- **Grounds** `bg900 #03100c` · `bg800 #06140f` · `bg700 #0a1c16` ·
  `surface #0c211a` · `surfaceRaised #0f2a21`
- **Accent** `accent #00e89a` · `accentDim #0bbf82` ·
  `accentGlow rgba(0,232,154,0.18)`
- **Gold** `gold #e8c46a` · `goldGlow rgba(232,196,106,0.55)`
- **Signal (data viz only)** `warn #f2a65a` · `danger #ef6f6f` · `info #5ab0f2`
- **Text** `ink #e7f3ee` · `inkStrong #ffffff` · `muted #8fa9a0` · `faint #5f746c`
- **Lines** `border rgba(255,255,255,0.06)` · `borderAccent rgba(0,232,154,0.16)`

Stated aesthetic target, verbatim from `tokens.ts`: *"a premium AI
visual-intelligence platform — deep, near-black greens; restrained luminous
accents; depth through layering and soft glows; tabular numerics. Not a
generic SaaS dashboard."*

**Signal colours are for data, not decoration.** Green does not mean "good"
in a palette where green is the brand accent — never encode a verdict in
accent green alone.

## Logo

`static/brand/ecoiq-logo.svg` — horizontal lockup, `viewBox="0 0 220 60"`,
40×40 icon mark (rounded square `#070b0f`, hexagon) plus the wordmark: **Eco
in white, IQ in accent green.** It carries `role="img"` and
`aria-label="EcoIQ"`; keep both. Its `<title>` reads *"EcoIQ — Ethical
Intelligence Platform"*.

Do not recolour the wordmark split, redraw the mark, stretch the viewBox, or
place the lockup on a light ground without checking contrast — the mark's own
background is near-black. Open-graph asset: `static/img/og-card.svg`.

## Typography

- App/marketing body: the system stack in `templates/base.html` —
  `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`.
  `tokens.ts` sets `font.sans: 'inherit'` deliberately; there is no webfont.
- Monospace / tabular numerics: `tokens.ts` `font.mono` —
  `"SF Mono", "JetBrains Mono", ui-monospace, "Roboto Mono", Menlo, monospace`.
  Numbers in tables and metrics use it.
- Eyebrow/label treatment in `system.css`: 11px, `letter-spacing: 0.16em`.

**No new font may be introduced** without an explicit decision — adding one
changes load behaviour and contradicts the deliberate `inherit`.

## Voice and tone

Derived from the platform's own system prompt
([`ai_gateway/prompts.py`](../../../ai_gateway/prompts.py)) and applied to
human-written copy too:

- Label what things are: **fact / assumption / estimate / recommendation**.
- "We do not have that data" is a good sentence. A plausible number is not.
- Decision-support, never advice — not legal, financial, medical, or
  religious.
- Institutional and specific over enthusiastic and vague. No exclamation
  marks, no "revolutionary", no "game-changing".

## Khalifah AI presentation

1. AI output is always visibly attributed as AI output.
2. It is **decision-support information — never a religious ruling (fatwa)**
   and never a substitute for a qualified scholar, lawyer, auditor, or
   physician. This sentence is already load-bearing in the system prompt;
   surfaced copy must not contradict it.
3. Confidence and review state travel with the output — see
   `ecoiq-evidence-audit`. Unreviewed AI evidence is shown as unreviewed.
4. No fabricated Qur'anic references, hadith, surah numbers, or KPI ids.

## Terminology policy — read before writing any public copy

[`docs/governance-principles-surah-map.md`](../../../docs/governance-principles-surah-map.md)
is marked **INTERNAL ONLY — NOT FOR PUBLIC DISPLAY, API RESPONSES, OR
MARKETING.** No Surah names, Arabic terminology, or Qur'anic references
appear in public-facing code, API responses, or marketing material. Public
surfaces use the professional English principle titles from that mapping
(principle 114 → *Consumer Protection & Anti-Manipulation*).

`docs/platform-overview.md` (Module 05 language guidance) holds the approved
and prohibited language list. Internal analyst tools and the advanced
methodology view are the exception, not the default.

## Language coverage — what is actually true today

Do not claim four-language parity.

| Surface | Reality |
|---|---|
| Django `LANGUAGES` | **`en` only.** `ru`/`kk`/`ar`/`tr` are commented out in `ecoiq/settings.py` ~line 408. |
| `locale/` catalogues | `ar`, `kk`, `ru`, `tr` present but not enabled. |
| AI assistant | `en`, `ar`, `ru` — `ai_gateway/prompts.py` `SUPPORTED_LANGUAGES`. **Kazakh is not supported by the assistant.** |

So: the assistant speaks three languages, the site ships one, and Kazakh
exists only as an unused catalogue. Any multilingual claim must match that.

## Decisions required (not invented here)

Absent from the repository; flag rather than fill:
- No written logo clear-space, minimum-size, or misuse rules.
- No light-mode brand palette — tokens are dark-only.
- No favicon/app-icon specification alongside the horizontal lockup.
- No approved boilerplate/company description.
- No defined Arabic or Cyrillic typographic treatment, despite `locale/ar`
  and `locale/ru` existing.
