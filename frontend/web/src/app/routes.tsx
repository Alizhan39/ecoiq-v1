import { lazy, Suspense } from 'react';
import { Route, Routes } from 'react-router-dom';
import { Loading } from '@/components/States';
import { useDocumentTitle } from './useDocumentTitle';

const Home = lazy(() => import('@/pages/Home'));
const Intelligence = lazy(() => import('@/pages/Intelligence'));
const Companies = lazy(() => import('@/pages/Companies'));
const Projects = lazy(() => import('@/pages/Projects'));
const ProjectConcept = lazy(() => import('@/pages/ProjectConcept'));
const Tours = lazy(() => import('@/pages/Tours'));
const About = lazy(() => import('@/pages/About'));
const Contact = lazy(() => import('@/pages/Contact'));
const League = lazy(() => import('@/pages/League'));
const Pricing = lazy(() => import('@/pages/Pricing'));
const Labs = lazy(() => import('@/pages/Labs'));
const TrustCenter = lazy(() => import('@/pages/TrustCenter'));
const NotFound = lazy(() => import('@/pages/NotFound'));

/**
 * /companies/:slug IS DELIBERATELY NOT ROUTED HERE.
 *
 * The directory (/companies) IS routed — see pages/Companies.tsx. The
 * individual organisation page is still served by Django, and the React
 * implementation (pages/CompanyDetail.tsx) is built but not claimed.
 *
 * Why: parity is not proven. The server-rendered company profile carries
 * eleven panels — ethics master scores, improvement roadmap, financing
 * readiness, financing matches, the QDF decision filter, data status, Shariah
 * screening, KPI alignment, controversies, watchlist and the stock strip. The
 * React page is a summary. Today every organisation in production falls
 * through to the evidence-pending page, so nobody sees those panels — but the
 * moment one organisation becomes publishable, claiming this route would
 * silently delete eleven public sections from its page.
 *
 * Routing a URL is a claim to own it. This one is not owned yet.
 *
 * CompanyDetail stays in the tree, with its tests, so the next phase starts
 * from working code rather than from a rewrite. To finish the migration:
 * audit those eleven panels against the product EcoIQ actually wants, expose
 * the survivors through API v2, build them here, prove parity for a PUBLISHED
 * organisation, then route /companies/:slug and repoint companies/urls.py.
 */
export function AppRoutes() {
  // Django titles the document for whatever URL was requested; client-side
  // navigation changes no document, so the tab has to be kept in step here.
  useDocumentTitle();

  return (
    <Suspense fallback={<Loading />}>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/intelligence" element={<Intelligence />} />
        <Route path="/companies" element={<Companies />} />
        <Route path="/projects" element={<Projects />} />
        <Route path="/projects/:slug" element={<ProjectConcept />} />
        <Route path="/tours" element={<Tours />} />
        <Route path="/about" element={<About />} />
        <Route path="/contact" element={<Contact />} />
        <Route path="/league" element={<League />} />
        <Route path="/pricing" element={<Pricing />} />
        <Route path="/labs" element={<Labs />} />
        <Route path="/trust" element={<TrustCenter />} />
        <Route path="*" element={<NotFound />} />
      </Routes>
    </Suspense>
  );
}
