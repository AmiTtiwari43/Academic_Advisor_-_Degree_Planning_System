import { Component, ErrorInfo, ReactNode } from 'react';
import { ErrorState } from '../components/ErrorState/ErrorState';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Uncaught error caught by ErrorBoundary:', error, errorInfo);
  }

  public handleReset = () => {
    this.setState({ hasError: false, error: null });
    window.location.reload();
  };

  public render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: '48px 24px', maxWidth: '640px', margin: '0 auto' }}>
          <ErrorState
            title="Application Error Encountered"
            message={
              this.state.error?.message ||
              'A client-side error occurred while rendering the academic interface.'
            }
            onRetry={this.handleReset}
          />
        </div>
      );
    }

    return this.props.children;
  }
}
