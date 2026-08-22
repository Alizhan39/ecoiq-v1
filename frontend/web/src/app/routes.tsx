import { lazy, Suspense } from 'react';
import { Route, Routes } from 'react-router-dom';
import { Loading } from '@/components/States';
import { useDocumentTitle } from './useDocumentTitle';

const Home = lazy(() => import('@/pages/Home'));
const Intelligence = lazy(() => import('@/pages/Intelligence'));
const Companies = lazy(() => import('@/pages/Companies'));
const CompanyDetail = lazy(() => import('@/pages/CompanyDetail'));
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
 * The full public product surface is routed here.
 *
 * /companies/:slug was the last route to move. It reads
 * /api/v2/companies/<slug>/assessment/, which applies the SAME publication
 * gate as every other surface and omits every panel key when an assessment is
 * not publishable — see docs/product/COMPANY_PAGE_PANELS.md for which of the
 * eleven server-rendered panels were kept, which moved behind sign-in, and
 * which was removed.
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
        <Route path="/companies/:slug" element={<CompanyDetail />} />
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
