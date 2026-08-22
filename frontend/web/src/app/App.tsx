import { BrowserRouter } from 'react-router-dom';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import { Nav } from './Nav';
import { AppRoutes } from './routes';

export function App() {
  return (
    <BrowserRouter>
      <a className="skip-link" href="#main">Skip to content</a>
      <Nav />
      <main id="main" className="main">
        <ErrorBoundary>
          <AppRoutes />
        </ErrorBoundary>
      </main>
      <footer className="footer">
        <p>
          EcoIQ presents assessments only where evidence supports them.{' '}
          <a href="/trust">How we handle evidence</a>
        </p>
        <p>
          {/* Reachable, not promoted. See the note in Nav.tsx.
              /companies/ and /gcc-investors/ are plain anchors to
              Django-served sections, not client-side routes — see
              app/routes.tsx.

              /gcc-investors/ is here because it fronts eight
              sitemap-registered pages and the footer is their only internal
              link. It used to be linked from the server-rendered homepage and
              from /pricing/; both are React now, so dropping it here would
              orphan all eight. */}
          <a href="/companies/">Companies</a> · <a href="/league">League</a> ·{' '}
          <a href="/pricing">Pricing</a> · <a href="/labs">EcoIQ Labs</a> ·{' '}
          <a href="/gcc-investors/">GCC investors</a>
        </p>
      </footer>
    </BrowserRouter>
  );
}
