import { Component, type ErrorInfo, type ReactNode } from 'react';
import ErrorState from '@/components/ui/ErrorState';

interface Props {
  children: ReactNode;
  title?: string;
}

interface State {
  hasError: boolean;
  message: string;
}

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, message: '' };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, message: error.message || 'Unexpected error' };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('ErrorBoundary caught:', error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <ErrorState
          title={this.props.title || 'Something went wrong'}
          message={this.state.message}
          onRetry={() => this.setState({ hasError: false, message: '' })}
        />
      );
    }
    return this.props.children;
  }
}
