import { NavLink } from 'react-router-dom';
import { useState } from 'react';

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
  { to: '/tours', label: 'Eco Tours' },
  { to: '/projects', label: 'Projects' },
  { to: '/about', label: 'About' },
  { to: '/contact', label: 'Contact' },
] as const;

export function Nav() {
  const [open, setOpen] = useState(false);

  return (
    <header className="nav">
      <NavLink to="/" className="nav__brand" onClick={() => setOpen(false)}>
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
            onClick={() => setOpen(false)}
            className={({ isActive }) =>
              isActive ? 'nav__link nav__link--active' : 'nav__link'
            }
          >
            {link.label}
          </NavLink>
        ))}
      </nav>
    </header>
  );
}
