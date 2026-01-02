/**
 * LexFlow Protocol - プロフィールページ (V3)
 */
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useWallet } from '../contexts/WalletContext';
import './Auth.css';

const API_BASE = '/api/v1';

export const ProfilePage: React.FC = () => {
    const navigate = useNavigate();
    const { user, logout } = useAuth();
    const { address, isConnected, connect } = useWallet();

    const [isLinkingWallet, setIsLinkingWallet] = useState(false);
    const [linkError, setLinkError] = useState('');
    const [linkSuccess, setLinkSuccess] = useState('');

    if (!user) {
        navigate('/login');
        return null;
    }

    const handleLinkWallet = async () => {
        if (!isConnected) {
            await connect();
            return;
        }

        setIsLinkingWallet(true);
        setLinkError('');
        setLinkSuccess('');

        try {
            // 1. Nonce取得
            const nonceRes = await fetch(`${API_BASE}/auth/wallet/nonce`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ address: address })
            });

            if (!nonceRes.ok) throw new Error('Nonce取得に失敗しました');
            const { message } = await nonceRes.json();

            // 2. MetaMaskで署名
            if (!window.ethereum) throw new Error('MetaMaskが見つかりません');
            const signature = await window.ethereum.request({
                method: 'personal_sign',
                params: [message, address]
            });

            // 3. 署名検証
            const verifyRes = await fetch(`${API_BASE}/auth/wallet/verify`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ address: address, signature, message })
            });

            if (!verifyRes.ok) throw new Error('署名検証に失敗しました');

            setLinkSuccess('ウォレットを正常に連携しました');
        } catch (err) {
            setLinkError(err instanceof Error ? err.message : 'ウォレット連携に失敗しました');
        } finally {
            setIsLinkingWallet(false);
        }
    };

    const handleLogout = () => {
        logout();
        navigate('/login');
    };

    const getInitials = (email: string) => {
        return email.substring(0, 2).toUpperCase();
    };

    const truncateAddress = (address: string) => {
        return `${address.slice(0, 6)}...${address.slice(-4)}`;
    };

    return (
        <div className="auth-page">
            <div className="auth-container" style={{ maxWidth: '500px' }}>
                <div className="profile-card">
                    <div className="profile-header">
                        <div className="profile-avatar">
                            {getInitials(user.email)}
                        </div>
                        <div className="profile-info">
                            <h2>{user.displayName || 'LexFlowユーザー'}</h2>
                            <p>{user.email}</p>
                        </div>
                    </div>

                    <div className="profile-section">
                        <h3>🔗 連携ウォレット</h3>
                        <div className="wallet-list">
                            {isConnected && address ? (
                                <div className="wallet-item">
                                    <span className="wallet-address">{truncateAddress(address)}</span>
                                    <span className="wallet-verified">✓ 接続中</span>
                                </div>
                            ) : (
                                <p style={{ color: 'var(--text-muted)', marginBottom: '0.75rem' }}>
                                    ウォレットが接続されていません
                                </p>
                            )}

                            {linkError && <div className="auth-error">{linkError}</div>}
                            {linkSuccess && (
                                <div className="auth-error" style={{
                                    background: 'rgba(16, 185, 129, 0.1)',
                                    borderColor: 'rgba(16, 185, 129, 0.3)',
                                    color: '#10b981'
                                }}>
                                    {linkSuccess}
                                </div>
                            )}

                            <button
                                className="add-wallet-button"
                                onClick={handleLinkWallet}
                                disabled={isLinkingWallet}
                            >
                                {isLinkingWallet
                                    ? '連携中...'
                                    : isConnected
                                        ? '🔐 ウォレットを認証'
                                        : '➕ ウォレットを接続'
                                }
                            </button>
                        </div>
                    </div>

                    <div className="profile-section">
                        <h3>⚙️ アカウント設定</h3>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                            <button
                                className="wallet-connect-button"
                                onClick={() => navigate('/workspaces')}
                            >
                                <span>🏢</span>
                                ワークスペース管理
                            </button>
                            <button
                                className="wallet-connect-button"
                                onClick={() => alert('パスワード変更機能（実装予定）')}
                            >
                                <span>🔒</span>
                                パスワード変更
                            </button>
                        </div>
                    </div>

                    <button
                        className="auth-button"
                        style={{
                            background: 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)',
                            marginTop: '1rem'
                        }}
                        onClick={handleLogout}
                    >
                        ログアウト
                    </button>
                </div>
            </div>
        </div>
    );
};

export default ProfilePage;
