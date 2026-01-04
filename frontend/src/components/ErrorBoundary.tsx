import { Component, type ErrorInfo, type ReactNode } from 'react';

interface Props {
    children: ReactNode;
    fallback?: ReactNode;
}

interface State {
    hasError: boolean;
    error: Error | null;
}

class ErrorBoundary extends Component<Props, State> {
    public state: State = {
        hasError: false,
        error: null
    };

    public static getDerivedStateFromError(error: Error): State {
        return { hasError: true, error };
    }

    public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
        // ログエラー
        if (import.meta.env.DEV) {
            console.error('Uncaught error:', error, errorInfo);
        }

        // In production, you could send to error reporting service
        // e.g., Sentry.captureException(error);
    }

    public render() {
        if (this.state.hasError) {
            if (this.props.fallback) {
                return this.props.fallback;
            }

            return (
                <div style={{
                    padding: '2rem',
                    maxWidth: '600px',
                    margin: '50px auto',
                    textAlign: 'center',
                    border: '1px solid #e74c3c',
                    borderRadius: '8px',
                    background: '#fff'
                }}>
                    <h2 style={{ color: '#e74c3c' }}>エラーが発生しました</h2>
                    <p>申し訳ございません。予期しないエラーが発生しました。</p>
                    <button
                        onClick={() => window.location.reload()}
                        style={{
                            padding: '0.75rem 1.5rem',
                            background: '#3498db',
                            color: 'white',
                            border: 'none',
                            borderRadius: '5px',
                            cursor: 'pointer',
                            marginTop: '1rem'
                        }}
                    >
                        ページを再読み込み
                    </button>
                </div>
            );
        }

        return this.props.children;
    }
}

export default ErrorBoundary;
