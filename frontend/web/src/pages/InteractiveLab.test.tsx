import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import InteractiveLab from './InteractiveLab';

// WebGL and camera hardware are not available in jsdom; exercise component
// registration and event handling independently of the rendering engine.
const load = vi.hoisted(() => vi.fn().mockResolvedValue({}));
vi.mock('@/features/interactive/viewerLoader', () => ({ loadViewer: load }));

beforeEach(() => {
  vi.restoreAllMocks();
  load.mockClear();
  vi.stubGlobal('isSecureContext', false);
  vi.stubGlobal('fetch', vi.fn().mockImplementation(async (url: string) => ({
    ok: true, status: 200,
    json: async () => url.includes('libraries') ? { count: 0, results: [] } : {
      id: 'stewardship-demo', model_url: '/static/models/stewardship-demo.glb',
      is_demo: true, verified: false, ar_modes: ['webxr', 'scene-viewer', 'quick-look'],
      hotspots: [{ id: 'energy', label: url.includes('lang=ar') ? 'الطاقة' : 'Energy',
        position: '-0.8 0.35 0', normal: '0 1 0', measurement: null, evidence_url: null }],
    },
  })));
});

describe('Interactive lab', () => {
  it('keeps 3D unloaded until requested and offers text interaction', async () => {
    const { container } = render(<InteractiveLab />);
    await screen.findByRole('button', { name: 'Energy' });
    expect(container.querySelector('model-viewer')).toBeNull();
    expect(load).not.toHaveBeenCalled();
    expect(screen.getByText(/No measured asset data/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Energy' }));
    expect(screen.getByText(/No measurement or supporting evidence/)).toBeInTheDocument();
  });

  it('loads the local model on demand and keeps AR disabled until detected', async () => {
    const { container } = render(<InteractiveLab />);
    await userEvent.click(await screen.findByRole('button', { name: 'Load 3D model' }));
    await screen.findByRole('button', { name: 'View in your space' });
    expect(container.querySelector('model-viewer')).toHaveAttribute('src', '/static/models/stewardship-demo.glb');
    expect(screen.getByRole('button', { name: 'View in your space' })).toBeDisabled();
  });

  it('keeps text available when model loading fails and offers a retry', async () => {
    const { container } = render(<InteractiveLab />);
    await userEvent.click(await screen.findByRole('button', { name: 'Load 3D model' }));
    await screen.findByRole('button', { name: 'View in your space' });
    fireEvent(container.querySelector('model-viewer')!, new Event('error'));
    expect(await screen.findByRole('alert')).toHaveTextContent(/could not start/);
    expect(screen.getByRole('button', { name: 'Load 3D model' })).toBeEnabled();
    expect(screen.getByRole('button', { name: 'Energy' })).toBeInTheDocument();
  });

  it('activates AR from a user gesture only when a secure device reports support', async () => {
    vi.stubGlobal('isSecureContext', true);
    const { container } = render(<InteractiveLab />);
    await userEvent.click(await screen.findByRole('button', { name: 'Load 3D model' }));
    const button = await screen.findByRole('button', { name: 'View in your space' });
    const activateAR = vi.fn().mockResolvedValue(undefined);
    const element = container.querySelector('model-viewer')!;
    Object.defineProperties(element, {
      canActivateAR: { value: true },
      activateAR: { value: activateAR },
      loaded: { value: true },
    });
    fireEvent(element, new Event('load'));
    await waitFor(() => expect(button).toBeEnabled());
    expect(activateAR).not.toHaveBeenCalled();
    await userEvent.click(button);
    expect(activateAR).toHaveBeenCalledOnce();
  });

  it('retains text interaction and retry when the viewer import fails', async () => {
    load.mockRejectedValueOnce(new Error('Network unavailable'));
    const { container } = render(<InteractiveLab />);
    await userEvent.click(await screen.findByRole('button', { name: 'Load 3D model' }));
    expect(await screen.findByRole('alert')).toHaveTextContent(/could not start/);
    expect(container.querySelector('model-viewer')).toBeNull();
    expect(screen.getByRole('button', { name: 'Energy' })).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Load 3D model' }));
    expect(await screen.findByRole('button', { name: 'View in your space' })).toBeDisabled();
  });

  it('requests Arabic from the API and sets RTL', async () => {
    const { container } = render(<InteractiveLab />);
    await screen.findByRole('button', { name: 'Energy' });
    await userEvent.selectOptions(screen.getByRole('combobox'), 'ar');
    await screen.findByRole('button', { name: 'الطاقة' });
    expect(container.querySelector('[lang="ar"]')).toHaveAttribute('dir', 'rtl');
    expect(vi.mocked(fetch).mock.calls.some(([url]) => String(url).includes('lang=ar'))).toBe(true);
  });
});


describe('Interactive lab recovery and focus', () => {
  it('keeps keyboard focus on retry after an import failure', async () => {
    load.mockRejectedValueOnce(new Error('Offline'));
    render(<InteractiveLab />);
    const button = await screen.findByRole('button', { name: 'Load 3D model' });
    button.focus();
    await userEvent.keyboard('{Enter}');
    await screen.findByRole('alert');
    expect(screen.getByRole('button', { name: 'Load 3D model' })).toHaveFocus();
  });

  it('restores focus after AR permission rejection without losing text', async () => {
    vi.stubGlobal('isSecureContext', true);
    const { container } = render(<InteractiveLab />);
    await userEvent.click(await screen.findByRole('button', { name: 'Load 3D model' }));
    const button = await screen.findByRole('button', { name: 'View in your space' });
    const element = container.querySelector('model-viewer')!;
    Object.defineProperties(element, {
      canActivateAR: { value: true },
      activateAR: { value: vi.fn().mockRejectedValue(new DOMException('Denied', 'NotAllowedError')) },
    });
    fireEvent(element, new Event('load'));
    await userEvent.click(button);
    await screen.findByRole('alert');
    expect(screen.getByRole('button', { name: 'Load 3D model' })).toHaveFocus();
    expect(screen.getByRole('button', { name: 'Energy' })).toBeEnabled();
    await userEvent.click(screen.getByRole('button', { name: 'Load 3D model' }));
    expect(await screen.findByRole('button', { name: 'View in your space' })).toBeDisabled();
  });

  it('does not steal text-interface focus when an AR status failure arrives', async () => {
    const { container } = render(<InteractiveLab />);
    await userEvent.click(await screen.findByRole('button', { name: 'Load 3D model' }));
    await screen.findByRole('button', { name: 'View in your space' });
    const textButton = container.querySelector<HTMLButtonElement>('.interactive-parts button')!;
    textButton.focus();
    fireEvent(container.querySelector('model-viewer')!, new CustomEvent('ar-status', {
      detail: { status: 'failed' },
    }));
    await screen.findByRole('alert');
    expect(textButton).toHaveFocus();
  });

  it('does not enable AR on insecure pages even when the viewer reports support', async () => {
    const { container } = render(<InteractiveLab />);
    await userEvent.click(await screen.findByRole('button', { name: 'Load 3D model' }));
    const button = await screen.findByRole('button', { name: 'View in your space' });
    const element = container.querySelector('model-viewer')!;
    Object.defineProperty(element, 'canActivateAR', { value: true });
    fireEvent(element, new Event('load'));
    expect(button).toBeDisabled();
  });
});
