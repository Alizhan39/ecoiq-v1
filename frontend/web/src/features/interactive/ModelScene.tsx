import { useEffect, useRef, useState } from 'react';
import type { ModelViewerElement } from '@google/model-viewer';
import type { Scene } from '@/api/interactive';
import { loadViewer } from './viewerLoader';

// A type-only import above costs no runtime bytes. Register the component
// only after the visitor chooses to load 3D, not during route preloading.
declare global {
  // React 18 requires JSX namespace augmentation for custom elements.
  // eslint-disable-next-line @typescript-eslint/no-namespace
  namespace JSX {
    interface IntrinsicElements {
      'model-viewer': React.DetailedHTMLProps<React.HTMLAttributes<ModelViewerElement>, ModelViewerElement> & {
        src: string;
        alt: string;
        ar?: boolean;
        'ar-modes'?: string;
        'camera-controls'?: boolean;
        'touch-action'?: string;
      };
    }
  }
}

interface Props {
  scene: Scene;
  selected: string;
  onSelect: (id: string) => void;
  labels: { load: string; loading: string; ar: string; fallback: string; error: string; alt: string };
}

export function ModelScene({ scene, selected, onSelect, labels }: Props) {
  const viewer = useRef<ModelViewerElement>(null);
  const region = useRef<HTMLElement>(null);
  const retry = useRef<HTMLButtonElement>(null);
  const restoreFocus = useRef(false);
  const alive = useRef(true);
  const [state, setState] = useState<'idle' | 'loading' | 'registered' | 'ready' | 'error'>('idle');
  const [canAR, setCanAR] = useState(false);
  const registered = state === 'registered';
  useEffect(() => {
    alive.current = true;
    return () => { alive.current = false; };
  }, []);

  useEffect(() => {
    if (state === 'error' && (restoreFocus.current || document.activeElement === region.current)) {
      retry.current?.focus();
    }
    restoreFocus.current = false;
  }, [state]);

  const fail = () => {
    if (!alive.current) return;
    restoreFocus.current = !!viewer.current?.contains(document.activeElement);
    setState('error');
    setCanAR(false);
  };

  useEffect(() => {
    const element = viewer.current;
    if (!element) return undefined;
    const loaded = () => {
      setState('ready');
      setCanAR(window.isSecureContext && element.canActivateAR);
    };
    const failed = () => {
      restoreFocus.current = element.contains(document.activeElement);
      setState('error');
      setCanAR(false);
    };
    const arStatus = (event: Event) => {
      if ((event as CustomEvent<{ status: string }>).detail.status === 'failed') failed();
    };
    element.addEventListener('load', loaded);
    element.addEventListener('error', failed);
    element.addEventListener('ar-status', arStatus);
    // Covers a cached model that finished before listeners attached.
    if (element.loaded) loaded();
    return () => {
      element.removeEventListener('load', loaded);
      element.removeEventListener('error', failed);
      element.removeEventListener('ar-status', arStatus);
    };
  }, [registered, scene.model_url]);

  const load = async () => {
    // Keep focus in the viewer when its load button is removed. Do not move it
    // again on success: the user may have continued into the text interface.
    if (document.activeElement === retry.current) region.current?.focus();
    setState('loading');
    try {
      await loadViewer();
      if (alive.current) setState('registered');
    } catch {
      if (alive.current) setState('error');
    }
  };

  return (
    <section ref={region} tabIndex={-1} className="interactive-viewer" aria-label={labels.alt}>
      {(state === 'idle' || state === 'error') && (
        <button ref={retry} type="button" onClick={() => void load()}>{labels.load}</button>
      )}
      {(state === 'loading' || state === 'registered') && <p role="status">{labels.loading}</p>}
      {state === 'error' && <p role="alert">{labels.error}</p>}
      {(state === 'registered' || state === 'ready') && (
        <model-viewer ref={viewer} src={scene.model_url} alt={labels.alt}
          ar ar-modes={scene.ar_modes.join(' ')} camera-controls touch-action="pan-y">
          {/* Override the native button: enable only after actual capability
              detection. activateAR runs directly in the user click gesture. */}
          <button slot="ar-button" type="button" disabled={!canAR}
            onClick={() => void viewer.current?.activateAR().catch(fail)}>{labels.ar}</button>
          {scene.hotspots.map((part) => (
            <button key={part.id} slot={`hotspot-${part.id}`} type="button"
              data-position={part.position} data-normal={part.normal}
              aria-pressed={selected === part.id} onClick={() => onSelect(part.id)}>
              {part.label}
            </button>
          ))}
        </model-viewer>
      )}
      {!canAR && <p className="state__detail">{labels.fallback}</p>}
    </section>
  );
}
