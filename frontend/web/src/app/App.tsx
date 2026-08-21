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
      </footer>
    </BrowserRouter>
  );
}
