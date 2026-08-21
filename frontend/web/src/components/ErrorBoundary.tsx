import { Component, type ErrorInfo, type ReactNode } from 'react';

interface Props { children: ReactNode }
interface State { error: Error | null }

/**
 * Stops one broken surface taking the whole app down.
 *
 * Class component because React has no hook equivalent for error boundaries.
 */
export class ErrorBoundary extends Component<Props, State> {
  override state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  override componentDidCatch(error: Error, info: ErrorInfo): void {
    // eslint-disable-next-line no-console
    console.error('Unhandled UI error', error, info.componentStack);
  }

  override render(): ReactNode {
    if (this.state.error) {
      return (
        <div className="state state--error" role="alert">
          <h2>Something went wrong</h2>
          <p className="state__detail">{this.state.error.message}</p>
        </div>
      );
    }
    return this.props.children;
  }
}
