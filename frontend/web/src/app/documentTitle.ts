/**
 * Keep the browser tab in step with the route.
 *
 * Django injects the correct <title> for whatever URL was requested, so a
 * direct load and a crawler both see the right one. Client-side navigation
 * changes no document, so without this the tab keeps whatever title the FIRST
 * page load carried — visible in the tab strip, in the history menu, and in a
 * bookmark made after navigating. Found in production verification: clicking
 * "Intelligence" from the homepage left the tab reading "EcoIQ — Evidence-backed
 * decision intelligence".
 *
 * TWO COPIES OF THE TITLES, AND WHY
 * ---------------------------------
 * The authoritative set is ROUTE_META in core/spa.py — that is what a crawler
 * reads, and what a page carries before any JavaScript runs. This is a mirror
 * for the client. Django cannot reach into a bundle at request time and a
 * bundle cannot import a Python dict, so short of shipping the map as embedded
 * JSON (a second request-time coupling for a handful of strings) there are two
 * copies.
 *
 * They are kept honest by test, not by hope: core/tests_spa.py asserts that the
 * routes ROUTE_META covers and the routes this file covers are the same set,
 * reading this file from disk. A route added to one and not the other fails.
 */
export const ROUTE_TITLES: Record<string, string> = {
  '/': 'EcoIQ — Evidence-backed decision intelligence',
  '/intelligence': 'Intelligence — EcoIQ',
  '/companies': 'Organisations — EcoIQ',
  '/principles': 'The 114 stewardship principles — EcoIQ',
  '/projects': 'Projects — EcoIQ',
  '/tours': 'Eco Tours — EcoIQ',
  '/about': 'About — EcoIQ',
  '/contact': 'Contact — EcoIQ',
  '/pricing': 'Pricing — EcoIQ',
  '/league': 'League — EcoIQ',
  '/labs': 'EcoIQ Labs — EcoIQ',
  '/trust': 'Trust Center — EcoIQ',
  '/industrial-modernisation': 'Industrial modernisation — EcoIQ',
  '/industrial-modernisation-preview': 'Industrial modernisation preview — EcoIQ',
};

const NOT_FOUND = 'Page not found — EcoIQ';

/**
 * The title for a path, or null when the server's title is the better one.
 *
 * `/projects/<slug>` returns null on purpose: its title is the concept's own
 * name, which core.spa.project_concept_spa_view already put in the document
 * and which this map has no business duplicating. Leaving the served title
 * alone is more correct than replacing it with a generic one.
 *
 * Anything else unrecognised gets the not-found title — a client-side
 * navigation to a URL that does not exist should read as one in the tab, the
 * same way a direct load of it does.
 */
export function titleFor(pathname: string): string | null {
  const key = pathname === '/' ? '/' : `/${pathname.replace(/^\/|\/$/g, '')}`;
  const title = ROUTE_TITLES[key];
  if (title) return title;
  if (key.startsWith('/projects/')) return null;
  // Same reasoning for an organisation page: its title is the organisation's
  // own name, which core.spa.company_spa_view already injected.
  if (key.startsWith('/companies/')) return null;
  // And for one principle: core.spa.principle_spa_view puts the principle's
  // number and title in the document, and 404s outside 1-114, so an id that
  // reaches the client is one the server already vouched for.
  if (key.startsWith('/principles/')) return null;
  return NOT_FOUND;
}
