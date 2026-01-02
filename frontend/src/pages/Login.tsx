/**
 * LexFlow Protocol - ログインページ (V3)
 */
import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import './Auth.css';

export const LoginPage: React.FC = () => {
    const navigate = useNavigate();
    const { login } = useAuth();

    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [isLoading, setIsLoading] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setIsLoading(true);

        try {
            await login(email, password);
            navigate('/dashboard');
        } catch (err) {
            setError(err instanceof Error ? err.message : 'ログインに失敗しました');
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="auth-page">
            <div className="auth-container">
                <div className="auth-header">
                    <h1 className="auth-title">ログイン</h1>
                    <p className="auth-subtitle">LexFlow Protocolへようこそ</p>
                </div>

                <form className="auth-form" onSubmit={handleSubmit}>
                    {error && <div className="auth-error">{error}</div>}

                    <div className="form-group">
                        <label htmlFor="email">メールアドレス</label>
                        <input
                            type="email"
                            id="email"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            placeholder="your@email.com"
                            required
                        />
                    </div>

                    <div className="form-group">
                        <label htmlFor="password">パスワード</label>
                        <input
                            type="password"
                            id="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            placeholder="••••••••"
                            autoComplete="current-password"
                            required
                        />
                    </div>

                    <button
                        type="submit"
                        className="auth-button"
                        disabled={isLoading}
                    >
                        {isLoading ? 'ログイン中...' : 'ログイン'}
                    </button>
                </form>

                <div className="auth-footer">
                    <p>アカウントをお持ちでない方は</p>
                    <Link to="/signup" className="auth-link">新規登録</Link>
                </div>

                <div className="auth-divider">
                    <span>または</span>
                </div>

                <button className="wallet-connect-button">
                    <span className="wallet-icon">🦊</span>
                    MetaMaskでログイン
                </button>
            </div>
        </div>
    );
};

export default LoginPage;
