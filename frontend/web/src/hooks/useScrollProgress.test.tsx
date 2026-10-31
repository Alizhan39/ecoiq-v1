import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useScrollProgress } from './useScrollProgress';

function Probe() {
  const { ref, progress } = useScrollProgress<HTMLDivElement>();
  return <div ref={ref} data-testid="probe">{progress.toFixed(3)}</div>;
}

function stubRect(top: number, height: number) {
  Element.prototype.getBoundingClientRect = function rect() {
    return { top, height, bottom: top + height, left: 0, right: 0,
      width: 100, x: 0, y: top, toJSON: () => ({}) } as DOMRect;
  };
}

beforeEach(() => {
  vi.unstubAllGlobals();
  Object.defineProperty(window, 'innerHeight', { value: 800, configurable: true });
});

describe('useScrollProgress', () => {
  it('measures on mount rather than waiting for a scroll', () => {
    /**
     * IntersectionObserver's first callback is async, and a backgrounded tab
     * never delivers one. Without an immediate measure, a section already on
     * screen paints its progress-0 frame and holds it.
     */
    stubRect(400, 200);
    vi.stubGlobal('IntersectionObserver', class {
      observe() {} unobserve() {} disconnect() {}
    });
    render(<Probe />);
    // top 400, height 200, viewport 800 -> (800-400)/(200+800) = 0.4
    expect(screen.getByTestId('probe')).toHaveTextContent('0.400');
  });

  it('reports 0 before the element enters the viewport', () => {
    stubRect(900, 200);
    vi.stubGlobal('IntersectionObserver', class {
      observe() {} unobserve() {} disconnect() {}
    });
    render(<Probe />);
    expect(screen.getByTestId('probe')).toHaveTextContent('0.000');
  });

  it('reports 1 once the element is fully past', () => {
    stubRect(-500, 200);
    vi.stubGlobal('IntersectionObserver', class {
      observe() {} unobserve() {} disconnect() {}
    });
    render(<Probe />);
    expect(screen.getByTestId('probe')).toHaveTextContent('1.000');
  });

  it('works without IntersectionObserver at all', () => {
    /** An old browser gets a working page, not a crash. */
    stubRect(400, 200);
    vi.stubGlobal('IntersectionObserver', undefined);
    expect(() => render(<Probe />)).not.toThrow();
    expect(screen.getByTestId('probe')).toHaveTextContent('0.400');
  });
});
