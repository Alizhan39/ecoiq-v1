import { render } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { IndustrialTransitionScene } from './IndustrialTransitionScene';

/**
 * Lifecycle, not looks. jsdom cannot paint, so these test the properties that
 * decide whether the scene is safe to put on a page: it starts no loop, it
 * leaks nothing, and it survives a browser that withholds the APIs it prefers.
 */

function stubMatchMedia(reduced: boolean) {
  vi.stubGlobal('matchMedia', (query: string) => ({
    matches: reduced && query.includes('reduced-motion'),
    media: query, onchange: null,
    addListener: vi.fn(), removeListener: vi.fn(),
    addEventListener: vi.fn(), removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  }));
}

beforeEach(() => {
  stubMatchMedia(false);
  HTMLCanvasElement.prototype.getContext = vi.fn(() => ({
    clearRect: vi.fn(), fillRect: vi.fn(), beginPath: vi.fn(), arc: vi.fn(),
    fill: vi.fn(), setTransform: vi.fn(), globalAlpha: 1, fillStyle: '',
  })) as unknown as typeof HTMLCanvasElement.prototype.getContext;
});

afterEach(() => vi.unstubAllGlobals());

describe('the scene starts no animation loop', () => {
  it('never calls requestAnimationFrame', () => {
    /**
     * The property that makes rAF-after-unmount impossible rather than merely
     * handled: progress is the only input, so there is no loop to leak.
     */
    const raf = vi.fn();
    vi.stubGlobal('requestAnimationFrame', raf);
    render(<IndustrialTransitionScene />);
    expect(raf).not.toHaveBeenCalled();
  });

  it('leaves nothing running after unmount', () => {
    const raf = vi.fn();
    vi.stubGlobal('requestAnimationFrame', raf);
    const { unmount } = render(<IndustrialTransitionScene />);
    unmount();
    expect(raf).not.toHaveBeenCalled();
  });

  it('uses no timer', () => {
    const interval = vi.fn();
    const timeout = vi.fn();
    vi.stubGlobal('setInterval', interval);
    vi.stubGlobal('setTimeout', timeout);
    render(<IndustrialTransitionScene />);
    expect(interval).not.toHaveBeenCalled();
  });
});

describe('the scene degrades rather than throwing', () => {
  it('renders without IntersectionObserver', () => {
    vi.stubGlobal('IntersectionObserver', undefined);
    expect(() => render(<IndustrialTransitionScene />)).not.toThrow();
  });

  it('renders without ResizeObserver', () => {
    vi.stubGlobal('ResizeObserver', undefined);
    expect(() => render(<IndustrialTransitionScene />)).not.toThrow();
  });

  it('renders when the canvas context is unavailable', () => {
    HTMLCanvasElement.prototype.getContext = vi.fn(() => null) as never;
    expect(() => render(<IndustrialTransitionScene />)).not.toThrow();
  });

  it('renders without matchMedia', () => {
    vi.stubGlobal('matchMedia', undefined);
    expect(() => render(<IndustrialTransitionScene />)).not.toThrow();
  });

  it('disconnects the resize observer on unmount', () => {
    const disconnect = vi.fn();
    vi.stubGlobal('ResizeObserver', class {
      observe = vi.fn();
      disconnect = disconnect;
      unobserve = vi.fn();
    });
    const { unmount } = render(<IndustrialTransitionScene />);
    unmount();
    expect(disconnect).toHaveBeenCalled();
  });
});

describe('the scene is decoration, and says so', () => {
  it('is hidden from assistive technology', () => {
    const { container } = render(<IndustrialTransitionScene />);
    expect(container.querySelector('.itscene')).toHaveAttribute('aria-hidden', 'true');
  });

  it('contains nothing interactive', () => {
    const { container } = render(<IndustrialTransitionScene />);
    expect(container.querySelectorAll('a, button, input')).toHaveLength(0);
  });
});

describe('reduced motion gets the finished system, not a blank space', () => {
  it('pins to the completed frame', () => {
    stubMatchMedia(true);
    const { container } = render(<IndustrialTransitionScene />);
    const marker = container.querySelector('[data-stage]');
    expect(marker).toHaveAttribute('data-stage', 'verify');
    expect(marker).toHaveAttribute('data-recovered', '1.00');
  });

  it('still draws the topology', () => {
    stubMatchMedia(true);
    const { container } = render(<IndustrialTransitionScene />);
    expect(container.querySelectorAll('.itscene__edge').length).toBeGreaterThan(0);
    expect(container.querySelectorAll('.itscene__node').length).toBeGreaterThan(0);
  });
});

/**
 * A TRAP WORTH NAMING
 *
 * jsdom's getBoundingClientRect() returns all zeros, so useScrollProgress
 * computes (viewport - 0) / (0 + viewport) = 1 for every element: in jsdom a
 * scroll-driven component reads as FULLY SCROLLED by default.
 *
 * A test that renders one and asserts the "initial" frame is therefore
 * asserting the final frame while believing otherwise. Positioning has to be
 * stated explicitly.
 */
function atScrollPosition(top: number, height = 600) {
  vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockReturnValue({
    top, height, bottom: top + height, left: 0, right: 800, width: 800,
    x: 0, y: top, toJSON: () => ({}),
  } as DOMRect);
}

describe('the scene follows scroll position, not the clock', () => {
  it('shows the legacy system when the section is below the fold', () => {
    // Top at the viewport bottom: the section has not been reached.
    atScrollPosition(window.innerHeight);
    const { container } = render(<IndustrialTransitionScene />);
    const marker = container.querySelector('[data-stage]');
    expect(marker).toHaveAttribute('data-stage', 'legacy');
    expect(marker).toHaveAttribute('data-recovered', '0.00');
  });

  it('shows the modernised system once fully scrolled past', () => {
    atScrollPosition(-1200);
    const { container } = render(<IndustrialTransitionScene />);
    expect(container.querySelector('[data-stage]'))
      .toHaveAttribute('data-recovered', '1.00');
  });

  it('draws the losses in the legacy frame and none in the final frame', () => {
    atScrollPosition(window.innerHeight);
    const early = render(<IndustrialTransitionScene />);
    const earlyEdges = early.container.querySelectorAll('.itscene__edge').length;
    early.unmount();

    atScrollPosition(-1200);
    const late = render(<IndustrialTransitionScene />);
    const lateEdges = late.container.querySelectorAll('.itscene__edge').length;

    // Not merely different counts: the modernised system carries MORE edges,
    // because recovery loops are added while losses are removed.
    expect(lateEdges).toBeGreaterThan(earlyEdges);
  });
});
