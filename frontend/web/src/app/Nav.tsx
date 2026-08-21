import { NavLink } from 'react-router-dom';
import { useCallback, useEffect, useState } from 'react';
import { useSession } from '@/hooks/useSession';
import type { Identity } from '@/types/session';

/**
 * The canonical public navigation. Five destinations, plus sign-in.
 *
 * Deliberately NOT here: Rankings, Countries, AI Agents, Compendium,
 * Framework, Methodology, Geo Intelligence. Those are either experiments
 * (which belong under Labs) or internal. A primary navigation that lists
 * thirty things is a statement that the product is thirty things.
 */
const LINKS = [
  { to: '/intelligence', label: 'Intelligence' },
  { to: '/projects', label: 'Projects' },
  { to: '/tours', label: 'Eco Tours' },
  { to: '/about', label: 'About' },
  { to: '/contact', label: 'Contact' },
] as const;

/**
 * Reachable, but not primary.
 *
 * Companies is a secondary EVIDENCE surface, not the product — it is where you
 * inspect what EcoIQ knows about an organisation, reached from Intelligence or
 * a direct link. Labs holds the experimental work. Putting either in the
 * primary nav would say the product is a data directory, or thirty prototypes.
 */
const SECONDARY = [
  { to: '/companies', label: 'Companies' },
  { to: '/labs', label: 'EcoIQ Labs' },
  { to: '/trust', label: 'Trust' },
] as const;

export function Nav() {
  const [open, setOpen] = useState(false);
  const { identity } = useSession();
  const close = useCallback(() => setOpen(false), []);

  // Escape closes the menu. Without it a keyboard user who opens the menu has
  // to tab through every link to get out of it.
  useEffect(() => {
    if (!open) return undefined;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpen(false);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open]);

  return (
    <header className="nav">
      <NavLink to="/" className="nav__brand" onClick={close}>
        EcoIQ
      </NavLink>

      <button
        type="button"
        className="nav__toggle"
        aria-expanded={open}
        aria-controls="primary-navigation"
        onClick={() => setOpen((value) => !value)}
      >
        <span className="visually-hidden">
          {open ? 'Close menu' : 'Open menu'}
        </span>
        <span aria-hidden="true">{open ? '✕' : '☰'}</span>
      </button>

      <nav
        id="primary-navigation"
        className={open ? 'nav__links nav__links--open' : 'nav__links'}
        aria-label="Primary"
      >
        {LINKS.map((link) => (
          <NavLink
            key={link.to}
            to={link.to}
            onClick={close}
            className={({ isActive }) =>
              isActive ? 'nav__link nav__link--active' : 'nav__link'
            }
          >
            {link.label}
          </NavLink>
        ))}

        {/* Secondary links appear inline on mobile, where there is no room
            for a separate row, and in the footer on desktop. Duplicating them
            here rather than hiding the mobile menu behind a second control. */}
        {/* No aria-hidden here. Visibility is a CSS media-query decision, and
            tying it to the MOBILE menu state hid these links from screen
            readers on desktop, where they are plainly visible. */}
        <span className="nav__secondary">
          {SECONDARY.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              onClick={close}
              className={({ isActive }) =>
                isActive ? 'nav__link nav__link--minor nav__link--active'
                  : 'nav__link nav__link--minor'
              }
            >
              {link.label}
            </NavLink>
          ))}
        </span>

        <SignInLink identity={identity} onNavigate={close} />
      </nav>
    </header>
  );
}


/**
 * Sign in, or the signed-in identity.
 *
 * Renders nothing while the session is still loading rather than flashing
 * "Sign in" at someone who is already signed in.
 */
function SignInLink({
  identity,
  onNavigate,
}: {
  identity: Identity;
  onNavigate: () => void;
}) {
  if (identity.authenticated) {
    return (
      <span className="nav__identity">
        {identity.username}
        {identity.is_staff ? <span className="nav__staff"> · staff</span> : null}
      </span>
    );
  }
  return (
    <a className="nav__link nav__link--signin" href="/login/" onClick={onNavigate}>
      Sign in
    </a>
  );
}
