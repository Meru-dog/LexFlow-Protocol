import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useWallet } from '../contexts/WalletContext';
import { api } from '../services/api';
import './Auth.css';

const API_BASE = '/api/v1';

export const ProfilePage: React.FC = () => {
    const navigate = useNavigate();
    const { user, logout } = useAuth();
    const { address, isConnected, connect } = useWallet();

    const [displayName, setDisplayName] = useState('');
    const [slackWebhook, setSlackWebhook] = useState('');
    const [isLoadingProfile, setIsLoadingProfile] = useState(true);
    const [isSaving, setIsSaving] = useState(false);

    const [isLinkingWallet, setIsLinkingWallet] = useState(false);
    const [linkError, setLinkError] = useState('');
    const [linkSuccess, setLinkSuccess] = useState('');
    const [saveMessage, setSaveMessage] = useState({ type: '', text: '' });
    const [isTestingSlack, setIsTestingSlack] = useState(false);

    useEffect(() => {
        if (user) {
            loadProfile();
        }
    }, [user]);

    const loadProfile = async () => {
        setIsLoadingProfile(true);
        try {
            const profile: any = await api.getProfile();
            setDisplayName(profile.display_name || '');
            setSlackWebhook(profile.slack_webhook_url || '');
        } catch (err) {
            console.error('Failed to load profile:', err);
        } finally {
            setIsLoadingProfile(false);
        }
    };

    const handleSaveProfile = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsSaving(true);
        setSaveMessage({ type: '', text: '' });

        try {
            await api.updateProfile({
                display_name: displayName,
                slack_webhook_url: slackWebhook
            });
            setSaveMessage({ type: 'success', text: 'プロフィールを更新しました' });
        } catch (err) {
            setSaveMessage({ type: 'error', text: '更新に失敗しました' });
        } finally {
            setIsSaving(false);
        }
    };

    const handleTestSlack = async () => {
        if (!slackWebhook) {
            setSaveMessage({ type: 'error', text: 'Webhook URLを入力してからテストしてください' });
            return;
        }

        setIsTestingSlack(true);
        setSaveMessage({ type: '', text: '' });

        try {
            const res: any = await api.testSlackNotification();
            if (res.success) {
                setSaveMessage({ type: 'success', text: res.message });
            } else {
                setSaveMessage({ type: 'error', text: res.message });
            }
        } catch (err: any) {
            setSaveMessage({ type: 'error', text: 'テスト送信に失敗しました: ' + err.message });
        } finally {
            setIsTestingSlack(false);
        }
    };

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
            <div className="auth-container" style={{ maxWidth: '600px' }}>
                <div className="profile-card">
                    <div className="profile-header">
                        <div className="profile-avatar">
                            {getInitials(user.email)}
                        </div>
                        <div className="profile-info">
                            <h2>{displayName || 'LexFlowユーザー'}</h2>
                            <p>{user.email}</p>
                        </div>
                    </div>

                    <form onSubmit={handleSaveProfile} className="profile-section">
                        <h3>👤 基本情報</h3>
                        <div className="auth-form-group">
                            <label>表示名</label>
                            <input
                                type="text"
                                value={displayName}
                                onChange={(e) => setDisplayName(e.target.value)}
                                placeholder="表示名を入力"
                                className="auth-input"
                            />
                        </div>
                        <div className="auth-form-group">
                            <label>Slack Webhook URL</label>
                            <input
                                type="url"
                                value={slackWebhook}
                                onChange={(e) => setSlackWebhook(e.target.value)}
                                placeholder="https://hooks.slack.com/services/..."
                                className="auth-input"
                            />
                            <p className="input-tip">承認リクエストや重要通知を受け取るためのWebhook URL</p>
                        </div>

                        {saveMessage.text && (
                            <div className={`save-message ${saveMessage.type}`}>
                                {saveMessage.text}
                            </div>
                        )}

                        <div style={{ display: 'flex', gap: '1rem' }}>
                            <button
                                type="submit"
                                className="auth-button"
                                disabled={isSaving || isLoadingProfile}
                                style={{ padding: '0.6rem 1rem', fontSize: '0.9rem', flex: 2 }}
                            >
                                {isSaving ? '保存中...' : '変更を保存'}
                            </button>
                            <button
                                type="button"
                                className="auth-button"
                                onClick={handleTestSlack}
                                disabled={isTestingSlack || isSaving || isLoadingProfile || !slackWebhook}
                                style={{
                                    padding: '0.6rem 1rem',
                                    fontSize: '0.9rem',
                                    flex: 1,
                                    background: 'linear-gradient(135deg, #0ea5e9 0%, #0284c7 100%)'
                                }}
                            >
                                {isTestingSlack ? '送信中...' : 'テスト送信'}
                            </button>
                        </div>
                    </form>

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
                                type="button"
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
                        <h3>⚙️ アカウント管理</h3>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                            <button
                                type="button"
                                className="wallet-connect-button"
                                onClick={() => navigate('/workspaces')}
                            >
                                <span>🏢</span>
                                ワークスペース管理
                            </button>
                            <button
                                type="button"
                                className="wallet-connect-button"
                                onClick={() => alert('パスワード変更機能（実装予定）')}
                            >
                                <span>🔒</span>
                                パスワード変更
                            </button>
                        </div>
                    </div>

                    <button
                        type="button"
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
