import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { titleFor } from './documentTitle';

/**
 * Sync document.title with the current route on client-side navigation.
 *
 * Deliberately does nothing on the FIRST render for a route the server already
 * titled — Django injected the right title into the document, and overwriting
 * it with an identical string is a no-op we would rather not perform at all.
 * `titleFor` returns null wherever the server's title is the better one.
 */
export function useDocumentTitle(): void {
  const { pathname } = useLocation();

  useEffect(() => {
    const title = titleFor(pathname);
    if (title && document.title !== title) document.title = title;
  }, [pathname]);
}
