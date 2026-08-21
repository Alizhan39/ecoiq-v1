import { lazy, Suspense } from 'react';
import { Route, Routes } from 'react-router-dom';
import { Loading } from '@/components/States';

const Home = lazy(() => import('@/pages/Home'));
const Intelligence = lazy(() => import('@/pages/Intelligence'));
const Projects = lazy(() => import('@/pages/Projects'));
const Tours = lazy(() => import('@/pages/Tours'));
const About = lazy(() => import('@/pages/About'));
const Contact = lazy(() => import('@/pages/Contact'));
const Companies = lazy(() => import('@/pages/Companies'));
const CompanyDetail = lazy(() => import('@/pages/CompanyDetail'));
const Labs = lazy(() => import('@/pages/Labs'));
const TrustCenter = lazy(() => import('@/pages/TrustCenter'));
const NotFound = lazy(() => import('@/pages/NotFound'));

export function AppRoutes() {
  return (
    <Suspense fallback={<Loading />}>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/intelligence" element={<Intelligence />} />
        <Route path="/projects" element={<Projects />} />
        <Route path="/tours" element={<Tours />} />
        <Route path="/about" element={<About />} />
        <Route path="/contact" element={<Contact />} />
        <Route path="/companies" element={<Companies />} />
        <Route path="/companies/:slug" element={<CompanyDetail />} />
        <Route path="/labs" element={<Labs />} />
        <Route path="/trust" element={<TrustCenter />} />
        <Route path="*" element={<NotFound />} />
      </Routes>
    </Suspense>
  );
}
