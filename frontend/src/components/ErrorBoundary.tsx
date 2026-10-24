import { Component, type ErrorInfo, type ReactNode } from 'react';

interface Props {
  /** Shown instead of the crashed subtree. */
  fallback: ReactNode;
  /** Optional: called once when an error is caught (for logging). */
  onError?: (error: Error, info: ErrorInfo) => void;
  children: ReactNode;
}

interface State {
  hasError: boolean;
}

/**
 * Generic React error boundary (task 3). Wrap the Map and the Manager panel so
 * a WebGL/worker/render crash shows a friendly fallback and never blanks the
 * whole page — the rest of the app (e.g. the planner) stays usable.
 */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    // Keep a console trail but never rethrow.
    console.error('ErrorBoundary caught:', error, info);
    this.props.onError?.(error, info);
  }

  render(): ReactNode {
    if (this.state.hasError) return this.props.fallback;
    return this.props.children;
  }
}
