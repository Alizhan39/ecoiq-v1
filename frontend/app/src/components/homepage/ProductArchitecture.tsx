/**
 * Product Architecture: one platform, three ways to use it.
 *
 * The information problem
 * ----------------------
 * A visitor leaving this section should remember exactly three names — Review,
 * Intelligence, Institutional — and nothing else. The legacy homepage failed at
 * this by showing the *capabilities* first: a five-module catalogue, a terminal
 * teaser and a country-report block, ~2,295px of surface that named a dozen
 * features and no products. Feature lists are what you read *after* you have
 * decided which product you are, not before.
 *
 * So the disclosure runs the other way round. Three products are stated plainly
 * and permanently. The eighteen capabilities behind them exist, but stay folded
 * until the visitor picks a product — at which point they unfold *as that
 * product's contents*, which is the relationship the flat catalogue could never
 * express. The motion is the teaching: capabilities visibly belong to a parent.
 *
 * Why the transitions are CSS and not Framer `animate` props
 * ----------------------------------------------------------
 * This island renders inside `MotionProvider` (`LazyMotion` + `domAnimation`,
 * `strict`), and its elements are `m.*` — but its motion is expressed in CSS.
 *
 * That is not a stylistic preference. Framer `animate` props were implemented
 * first, three different ways (`AnimatePresence` mount/unmount, always-mounted
 * `animate`, and variants), and in every version the values were written once
 * at mount and never updated again: `data-open`/`data-quiet` flipped correctly
 * on the same elements — proving React re-rendered them with new props — while
 * the animated `opacity`, `height` and `rotate` stayed frozen at their initial
 * values, sampled every 70ms across the full duration. The sibling
 * `DecisionPipeline` island animates normally on the same page under the same
 * provider, so the cause is specific to this tree and is not understood yet.
 *
 * A React-rendered inline <style> was tried next: its sheet parsed (14 rules,
 * correct selectors, matching elements) but never appeared in
 * `document.styleSheets`, so none of it applied either.
 *
 * What ships is `src/product-architecture.css`, imported through `main.tsx`
 * like every other island stylesheet in this codebase — the only variant that
 * measurably applies. It uses the LOCKED motion values verbatim: 0.18s
 * (`duration.fast`), 0.42s (`duration.base`), cubic-bezier(0.22, 1, 0.36, 1)
 * (`ease.out`), and a 60ms row stagger (`duration.fast / 3`). Those are
 * literals in the CSS rather than interpolations, so they can drift from
 * `tokens.ts` if the tokens ever change — the stylesheet says so at the top.
 * No new tokens are introduced, and only `opacity`, `transform` and
 * `grid-template-rows` animate. The `m.*` elements and the provider stay in
 * place, so this can move back onto Framer `animate` props without touching
 * the markup once the root cause is found.
 *
 * Reduced motion
 * --------------
 * A `prefers-reduced-motion: reduce` block disables every transition and shows
 * capability rows at their resting position immediately. Disclosure still
 * works; only the interpolation is removed. No information is animation-gated.
 */
import { m } from 'framer-motion'
import { useCallback, useId, useState } from 'react'

import { color, font, radius } from '../../design/tokens'
import { useMediaQuery } from '../../hooks/useMediaQuery'

type Capability = {
  label: string
  /** Optional deeper route. Carries forward links the legacy blocks owned. */
  href?: string
}

type Product = {
  id: string
  name: string
  audience: string
  copy: string
  price?: string
  scope?: string
  cta: { label: string; href: string }
  capabilities: Capability[]
  /** Review is the commercial entry point and reads slightly louder. */
  emphasis: 'primary' | 'standard'
}

export type ProductArchitectureProps = {
  /** Django-resolved URLs, passed as data-props so routes stay server-owned. */
  reviewHref?: string
  intelligenceHref?: string
  institutionalHref?: string
}

function buildProducts({
  reviewHref = '/request-access/review/',
  intelligenceHref = '/platform/',
  institutionalHref = '/request-access/enterprise/',
}: ProductArchitectureProps): Product[] {
  return [
    {
      id: 'review',
      name: 'EcoIQ Review',
      audience: 'Companies & projects',
      copy: 'Understand the risks, evidence gaps, financing readiness and what should happen next.',
      price: 'From £4,900',
      scope: 'Single company or project',
      cta: { label: 'Request Review', href: reviewHref },
      emphasis: 'primary',
      capabilities: [
        { label: 'Evidence' },
        { label: 'Transition Risk' },
        { label: 'Governance' },
        // Preserves the legacy modules block's only deep anchor.
        { label: 'Capital Readiness', href: '/platform/#capital-integrity' },
        { label: 'Ethical Finance' },
        { label: '90-Day Roadmap' },
      ],
    },
    {
      id: 'intelligence',
      name: 'EcoIQ Intelligence',
      audience: 'Investors, funds & analysts',
      copy: 'Screen opportunities, compare companies and markets, and identify decision signals at scale.',
      cta: { label: 'Explore Intelligence', href: intelligenceHref },
      emphasis: 'standard',
      capabilities: [
        { label: 'Companies', href: '/companies/' },
        { label: 'Countries', href: '/countries/' },
        { label: 'Projects', href: '/projects/' },
        { label: 'Rankings', href: '/companies/' },
        { label: 'Comparisons', href: '/platform/' },
        // Preserves the terminal block's demo-request destination.
        {
          label: 'Terminal',
          href: 'mailto:alizhan@ecoiq.uk?subject=Intelligence+Terminal+Demo+Request',
        },
      ],
    },
    {
      id: 'institutional',
      name: 'EcoIQ Institutional',
      audience: 'Banks, funds, corporations & governments',
      copy: 'Custom intelligence for portfolios, sectors, sovereign mandates and large-scale implementation.',
      cta: { label: 'Discuss Engagement', href: institutionalHref },
      emphasis: 'standard',
      capabilities: [
        { label: 'Portfolio Intelligence' },
        { label: 'Sector Analysis' },
        // Preserves the country-intelligence block's destination.
        { label: 'Sovereign Intelligence', href: '/countries/' },
        { label: 'API / Data' },
        { label: 'Monitoring' },
        { label: 'Implementation' },
      ],
    },
  ]
}

export default function ProductArchitecture(props: ProductArchitectureProps) {
  const products = buildProducts(props)
  /**
   * Pointer capability, not width: a narrow desktop window still hovers, and a
   * large tablet still does not. Hover-to-preview is enabled only where hover
   * genuinely exists, so touch devices never depend on it.
   */
  const canHover = useMediaQuery('(hover: hover) and (pointer: fine)')
  const baseId = useId()

  /** Pinned by click / Enter / Space. Survives the pointer leaving. */
  const [pinned, setPinned] = useState<string | null>(null)
  /** Previewed by hover or focus, on hover-capable pointers only. */
  const [preview, setPreview] = useState<string | null>(null)

  const openId = (canHover ? (preview ?? pinned) : pinned) ?? null

  const toggle = useCallback((id: string) => {
    setPinned((current) => (current === id ? null : id))
  }, [])

  return (
    <section
      className="eiq-mo-root eiq-pa"
      aria-labelledby={`${baseId}-title`}
      style={{ padding: '4.5rem 1.5rem', borderTop: `1px solid ${color.border}` }}
    >
      <div style={{ maxWidth: 1120, margin: '0 auto' }}>
        <header style={{ maxWidth: 640, marginBottom: '2.5rem' }}>
          <h2
            id={`${baseId}-title`}
            style={{
              fontSize: 'clamp(1.6rem, 3.2vw, 2.3rem)',
              lineHeight: 1.15,
              letterSpacing: '-0.02em',
              color: color.inkStrong,
              margin: '0 0 0.75rem',
            }}
          >
            One platform. Three ways to use it.
          </h2>
          <p style={{ color: color.muted, fontSize: '1.02rem', lineHeight: 1.6, margin: 0 }}>
            EcoIQ combines evidence, risk, capital and stewardship intelligence
            differently depending on the decision you need to make.
          </p>
        </header>

        <ul className="eiq-pa-grid" role="list">
          {products.map((product) => (
            <ProductCard
              key={product.id}
              product={product}
              panelId={`${baseId}-${product.id}-panel`}
              open={openId === product.id}
              quiet={openId !== null && openId !== product.id}
              canHover={canHover}
              onToggle={toggle}
              onPreview={setPreview}
            />
          ))}
        </ul>
      </div>

    </section>
  )
}

type CardProps = {
  product: Product
  panelId: string
  open: boolean
  quiet: boolean
  canHover: boolean
  onToggle: (id: string) => void
  onPreview: (id: string | null) => void
}

function ProductCard({
  product,
  panelId,
  open,
  quiet,
  canHover,
  onToggle,
  onPreview,
}: CardProps) {
  const primary = product.emphasis === 'primary'

  /**
   * Hover and focus preview only where hover exists. On touch, focus follows
   * the tap that already toggled the card, so previewing there would fight the
   * pinned state.
   */
  const hoverHandlers = canHover
    ? {
        onMouseEnter: () => onPreview(product.id),
        onMouseLeave: () => onPreview(null),
        onFocus: () => onPreview(product.id),
        onBlur: () => onPreview(null),
      }
    : {}

  return (
    <m.li
      className="eiq-pa-card"
      data-product={product.id}
      data-open={open ? 'true' : 'false'}
      data-quiet={quiet ? 'true' : 'false'}
      style={{
        background: primary ? color.surfaceRaised : color.surface,
        border: `1px solid ${primary ? color.borderAccent : color.border}`,
        borderRadius: radius.lg,
        padding: '1.5rem 1.4rem',
        display: 'flex',
        flexDirection: 'column',
        gap: '0.85rem',
      }}
      {...hoverHandlers}
    >
      <button
        type="button"
        className="eiq-pa-toggle"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => onToggle(product.id)}
        style={{
          appearance: 'none',
          background: 'none',
          border: 'none',
          padding: 0,
          margin: 0,
          font: 'inherit',
          color: 'inherit',
          textAlign: 'left',
          cursor: 'pointer',
          display: 'flex',
          flexDirection: 'column',
          gap: '0.4rem',
          width: '100%',
        }}
      >
        <span
          style={{
            fontFamily: font.mono,
            fontSize: '0.66rem',
            letterSpacing: '0.14em',
            textTransform: 'uppercase',
            color: primary ? color.accent : color.faint,
          }}
        >
          {product.audience}
        </span>
        <span
          style={{
            display: 'flex',
            alignItems: 'baseline',
            justifyContent: 'space-between',
            gap: '0.6rem',
          }}
        >
          <span
            style={{
              fontSize: primary ? '1.35rem' : '1.2rem',
              fontWeight: 600,
              letterSpacing: '-0.015em',
              color: color.inkStrong,
            }}
          >
            {product.name}
          </span>
          <span
            className="eiq-pa-icon"
            aria-hidden="true"
            style={{
              flex: '0 0 auto',
              width: 20,
              height: 20,
              display: 'grid',
              placeItems: 'center',
              borderRadius: radius.pill,
              border: `1px solid ${color.border}`,
              color: color.muted,
              fontSize: '0.85rem',
              lineHeight: 1,
            }}
          >
            +
          </span>
        </span>
      </button>

      <p style={{ margin: 0, color: color.ink, fontSize: '0.94rem', lineHeight: 1.55 }}>
        {product.copy}
      </p>

      {(product.price || product.scope) && (
        <p
          style={{
            margin: 0,
            display: 'flex',
            flexWrap: 'wrap',
            alignItems: 'baseline',
            gap: '0.5rem',
          }}
        >
          {product.price && (
            <span
              style={{
                fontFamily: font.mono,
                fontSize: '1rem',
                color: color.accent,
                letterSpacing: '-0.01em',
              }}
            >
              {product.price}
            </span>
          )}
          {product.scope && (
            <span style={{ fontSize: '0.82rem', color: color.faint }}>{product.scope}</span>
          )}
        </p>
      )}

      {/*
        The disclosure panel is always mounted so `aria-controls` always
        resolves to a real element, and it collapses via grid rows rather than
        being unmounted. `aria-hidden` tracks `open`, so what assistive
        technology is offered and what `aria-expanded` claims can never
        disagree: collapsed capabilities are not announced as available text,
        expanded ones are fully readable.
      */}
      <m.div id={panelId} className="eiq-pa-panel" aria-hidden={!open}>
        <div className="eiq-pa-panel-inner">
          <ul
            className="eiq-pa-cap"
            role="list"
            style={{
              listStyle: 'none',
              margin: '0.35rem 0 0',
              padding: 0,
              display: 'grid',
              gridTemplateColumns: '1fr 1fr',
              gap: '0.4rem 0.9rem',
            }}
          >
            {product.capabilities.map((capability, index) => (
              <li
                key={capability.label}
                style={
                  {
                    '--i': index,
                    fontSize: '0.82rem',
                    color: color.muted,
                    borderTop: `1px solid ${color.border}`,
                    paddingTop: '0.4rem',
                  } as React.CSSProperties
                }
              >
                {capability.href ? (
                  <a href={capability.href} style={{ color: 'inherit', textDecoration: 'none' }}>
                    {capability.label}
                  </a>
                ) : (
                  capability.label
                )}
              </li>
            ))}
          </ul>
        </div>
      </m.div>

      <a
        className="eiq-pa-cta"
        href={product.cta.href}
        style={{
          marginTop: 'auto',
          display: 'inline-flex',
          alignItems: 'center',
          justifyContent: 'center',
          /* 44px minimum touch target. */
          minHeight: 44,
          padding: '0.6rem 1.1rem',
          borderRadius: radius.pill,
          fontSize: '0.88rem',
          fontWeight: 600,
          textDecoration: 'none',
          background: primary ? color.accent : 'transparent',
          color: primary ? color.bg900 : color.ink,
          border: `1px solid ${primary ? color.accent : color.borderAccent}`,
        }}
      >
        {product.cta.label}
      </a>
    </m.li>
  )
}
