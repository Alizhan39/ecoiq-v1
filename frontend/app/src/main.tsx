/**
 * EcoIQ Visual Intelligence — island loader.
 *
 * This is the single entry point compiled to static/dist/ecoiq-islands.js.
 * It hydrates "islands": any element in a Django template marked with
 *
 *     <div data-island="ImpactGlobe" data-props='{"villages": 12, ...}'></div>
 *
 * gets a React component mounted into it, with `data-props` (JSON) passed as
 * props. Django stays the page shell and the source of truth for data — it
 * simply embeds JSON. Nothing here calls AI/APIs or holds secrets.
 *
 * Design rules for this layer:
 *   - Fail safe: an unknown island or bad JSON logs a warning and leaves the
 *     server-rendered fallback markup untouched. A page never breaks.
 *   - Idempotent: elements are marked once mounted; mountAll() can be re-run
 *     after dynamic content is injected (exposed as window.EcoIQIslands).
 */
import { createElement } from 'react'
import { createRoot } from 'react-dom/client'
import './design/system.css'
import './islands.css'
import { MotionProvider } from './motion'
import { registry } from './registry'

type Props = Record<string, unknown>

function parseProps(el: HTMLElement): Props {
  const raw = el.getAttribute('data-props')
  if (!raw) return {}
  try {
    return JSON.parse(raw) as Props
  } catch (err) {
    console.error('[ecoiq-islands] invalid data-props JSON on', el, err)
    return {}
  }
}

function mountOne(el: HTMLElement): void {
  const name = el.getAttribute('data-island') ?? ''
  const Component = registry[name]
  if (!Component) {
    console.warn(`[ecoiq-islands] unknown island "${name}" — leaving fallback`)
    return
  }
  el.setAttribute('data-island-mounted', '')
  el.classList.add('eiq') // scope design-system CSS variables to the island
  try {
    createRoot(el).render(
      createElement(MotionProvider, null, createElement(Component, parseProps(el))),
    )
  } catch (err) {
    console.error(`[ecoiq-islands] failed to mount "${name}"`, err)
    el.removeAttribute('data-island-mounted')
  }
}

/** Mount every not-yet-mounted island found under `root`.
 *  Islands marked `data-island-lazy` defer mounting until they approach the
 *  viewport (IntersectionObserver, 400px margin) to keep initial work small. */
export function mountAll(root: ParentNode = document): void {
  const nodes = root.querySelectorAll<HTMLElement>(
    '[data-island]:not([data-island-mounted])',
  )
  const lazy: HTMLElement[] = []
  nodes.forEach((el) => {
    if (el.hasAttribute('data-island-lazy') && 'IntersectionObserver' in window) {
      lazy.push(el)
    } else {
      mountOne(el)
    }
  })
  if (lazy.length) {
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            io.unobserve(entry.target)
            mountOne(entry.target as HTMLElement)
          }
        })
      },
      { rootMargin: '400px 0px' },
    )
    lazy.forEach((el) => io.observe(el))
  }
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => mountAll())
} else {
  mountAll()
}

// Public hook for future phases (e.g. re-hydrate after HTMX/dynamic swaps).
declare global {
  interface Window {
    EcoIQIslands?: { mountAll: typeof mountAll; registry: typeof registry }
  }
}
window.EcoIQIslands = { mountAll, registry }
