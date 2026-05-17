import React from 'react';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('Dashboard error:', error, errorInfo);
    this.setState({ errorInfo });
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          display: 'flex', flexDirection: 'column', alignItems: 'center',
          justifyContent: 'center', height: '100vh', padding: '20px',
          textAlign: 'center', background: '#1a1a2e', color: '#e0e0e0'
        }}>
          <h2 style={{ color: '#f44336', marginBottom: '16px' }}>Something went wrong</h2>
          <p style={{ marginBottom: '8px' }}>{this.state.error?.message || 'An unexpected error occurred'}</p>
          <details style={{ margin: '20px', textAlign: 'left', maxWidth: '600px' }}>
            <summary style={{ cursor: 'pointer', color: '#888' }}>Technical details</summary>
            <pre style={{ fontSize: '12px', overflow: 'auto', background: '#0d0d1a', padding: '12px', borderRadius: '4px', marginTop: '8px' }}>
              {this.state.error?.stack}
              {'\n\n'}
              {this.state.errorInfo?.componentStack}
            </pre>
          </details>
          <button
            onClick={() => window.location.reload()}
            style={{
              padding: '10px 24px', background: '#4caf50', color: 'white',
              border: 'none', borderRadius: '6px', cursor: 'pointer',
              marginTop: '20px', fontSize: '14px'
            }}
          >
            Reload Dashboard
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

export default ErrorBoundary;
