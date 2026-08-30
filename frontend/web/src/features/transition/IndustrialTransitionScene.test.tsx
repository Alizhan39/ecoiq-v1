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
    render(<IndustrialTransitionScene progress={0} />);
    expect(raf).not.toHaveBeenCalled();
  });

  it('leaves nothing running after unmount', () => {
    const raf = vi.fn();
    vi.stubGlobal('requestAnimationFrame', raf);
    const { unmount } = render(<IndustrialTransitionScene progress={0} />);
    unmount();
    expect(raf).not.toHaveBeenCalled();
  });

  it('uses no timer', () => {
    const interval = vi.fn();
    const timeout = vi.fn();
    vi.stubGlobal('setInterval', interval);
    vi.stubGlobal('setTimeout', timeout);
    render(<IndustrialTransitionScene progress={0} />);
    expect(interval).not.toHaveBeenCalled();
  });
});

describe('the scene degrades rather than throwing', () => {
  it('renders without IntersectionObserver', () => {
    vi.stubGlobal('IntersectionObserver', undefined);
    expect(() => render(<IndustrialTransitionScene progress={0} />)).not.toThrow();
  });

  it('renders without ResizeObserver', () => {
    vi.stubGlobal('ResizeObserver', undefined);
    expect(() => render(<IndustrialTransitionScene progress={0} />)).not.toThrow();
  });

  it('renders when the canvas context is unavailable', () => {
    HTMLCanvasElement.prototype.getContext = vi.fn(() => null) as never;
    expect(() => render(<IndustrialTransitionScene progress={0} />)).not.toThrow();
  });

  it('renders without matchMedia', () => {
    vi.stubGlobal('matchMedia', undefined);
    expect(() => render(<IndustrialTransitionScene progress={0} />)).not.toThrow();
  });

  it('disconnects the resize observer on unmount', () => {
    const disconnect = vi.fn();
    vi.stubGlobal('ResizeObserver', class {
      observe = vi.fn();
      disconnect = disconnect;
      unobserve = vi.fn();
    });
    const { unmount } = render(<IndustrialTransitionScene progress={0} />);
    unmount();
    expect(disconnect).toHaveBeenCalled();
  });
});

describe('the scene is decoration, and says so', () => {
  it('is hidden from assistive technology', () => {
    const { container } = render(<IndustrialTransitionScene progress={0} />);
    expect(container.querySelector('.itscene')).toHaveAttribute('aria-hidden', 'true');
  });

  it('contains nothing interactive', () => {
    const { container } = render(<IndustrialTransitionScene progress={0} />);
    expect(container.querySelectorAll('a, button, input')).toHaveLength(0);
  });
});

describe('reduced motion gets the finished system, not a blank space', () => {
  it('pins to the completed frame', () => {
    stubMatchMedia(true);
    const { container } = render(<IndustrialTransitionScene progress={0} />);
    const marker = container.querySelector('[data-stage]');
    expect(marker).toHaveAttribute('data-stage', 'verify');
    expect(marker).toHaveAttribute('data-recovered', '1.00');
  });

  it('still draws the topology', () => {
    stubMatchMedia(true);
    const { container } = render(<IndustrialTransitionScene progress={0} />);
    expect(container.querySelectorAll('.itscene__edge').length).toBeGreaterThan(0);
    expect(container.querySelectorAll('.itscene__node').length).toBeGreaterThan(0);
  });
});


describe('the scene follows the progress it is given, not the clock', () => {
  /**
   * These used to stub getBoundingClientRect and let the component measure its
   * own scroll position. It cannot any more, and should not have: the scene
   * sits inside a position:sticky panel, so its own element never moves as the
   * page scrolls and its internal measurement froze — the drawing showed
   * modernised equipment at the legacy stage because progress never advanced.
   *
   * Progress now comes from the page that owns the scroll container, so these
   * pass it directly. That is both the real contract and a stricter test: no
   * layout stub sits between the input and the assertion.
   */
  it('shows the legacy system at progress 0', () => {
    const { container } = render(<IndustrialTransitionScene progress={0} />);
    const marker = container.querySelector('[data-stage]');
    expect(marker).toHaveAttribute('data-stage', 'legacy');
    expect(marker).toHaveAttribute('data-recovered', '0.00');
  });

  it('shows the modernised system at progress 1', () => {
    const { container } = render(<IndustrialTransitionScene progress={1} />);
    const marker = container.querySelector('[data-stage]');
    expect(marker).toHaveAttribute('data-stage', 'verify');
    expect(marker).toHaveAttribute('data-recovered', '1.00');
  });

  it('does not show modernised equipment at the legacy stage', () => {
    // The bug this file exists to prevent recurring: a frozen progress made
    // the variable-speed drive and the electric heater visible beside the
    // boiler they replace.
    const { container } = render(<IndustrialTransitionScene progress={0} />);
    const labels = [...container.querySelectorAll('.itscene__label')]
      .map((n) => n.textContent);
    expect(labels).toContain('Fired process heat');
    expect(labels).not.toContain('Variable-speed drive');
    expect(labels).not.toContain('Electrified process heat');
  });

  it('replaces that equipment by the end', () => {
    const { container } = render(<IndustrialTransitionScene progress={1} />);
    const labels = [...container.querySelectorAll('.itscene__label')]
      .map((n) => n.textContent);
    expect(labels).not.toContain('Fired process heat');
    expect(labels).toContain('Electrified process heat');
    expect(labels).toContain('Variable-speed drive');
  });

  it('draws the losses in the legacy frame and more routes in the final one', () => {
    const early = render(<IndustrialTransitionScene progress={0} />);
    const earlyEdges = early.container.querySelectorAll('.itscene__edge').length;
    early.unmount();

    const late = render(<IndustrialTransitionScene progress={1} />);
    const lateEdges = late.container.querySelectorAll('.itscene__edge').length;

    // Not merely different counts: the modernised system carries MORE edges,
    // because recovery loops are added while losses are removed.
    expect(lateEdges).toBeGreaterThan(earlyEdges);
  });
});
