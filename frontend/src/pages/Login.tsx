/**
 * LexFlow Protocol - ログインページ (V3)
 */
import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useWallet } from '../contexts/WalletContext';
import './Auth.css';

export const LoginPage: React.FC = () => {
    const navigate = useNavigate();
    const { login } = useAuth();
    const { connect, isConnected, address } = useWallet();

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
            navigate('/');
        } catch (err) {
            setError(err instanceof Error ? err.message : 'ログインに失敗しました');
        } finally {
            setIsLoading(false);
        }
    };

    const handleMetaMaskLogin = async () => {
        setError('');
        setIsLoading(true);

        try {
            // 1. ウォレット接続
            if (!isConnected) {
                await connect();
            }

            // 2. 接続されたウォレットアドレスを取得
            const walletAddress = address || (await window.ethereum.request({ method: 'eth_accounts' }))[0];

            if (!walletAddress) {
                throw new Error('ウォレットアドレスが取得できませんでした');
            }

            // 3. バックエンドから nonce を取得
            const nonceRes = await fetch('/api/v1/auth/wallet/nonce', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ address: walletAddress })
            });

            if (!nonceRes.ok) throw new Error('Nonce取得に失敗しました');
            const { message } = await nonceRes.json();

            // 4. MetaMaskで署名
            const signature = await window.ethereum.request({
                method: 'personal_sign',
                params: [message, walletAddress]
            });

            // 5.署名検証
            const verifyRes = await fetch('/api/v1/auth/wallet/verify', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ address: walletAddress, signature, message })
            });

            if (!verifyRes.ok) throw new Error('署名検証に失敗しました');

            // 6. ログイン時刻を保存（MetaMaskログインも1時間制限を適用）
            localStorage.setItem('login_timestamp', Date.now().toString());

            // 7. Homeに遷移
            navigate('/');
        } catch (err) {
            setError(err instanceof Error ? err.message : 'MetaMaskログインに失敗しました');
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

                <button
                    className="wallet-connect-button"
                    onClick={handleMetaMaskLogin}
                    disabled={isLoading}
                >
                    <span className="wallet-icon">🦊</span>
                    MetaMaskでログイン
                </button>
            </div>
        </div>
    );
};

export default LoginPage;
