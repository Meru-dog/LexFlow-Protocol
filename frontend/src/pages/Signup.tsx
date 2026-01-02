/**
 * LexFlow Protocol - サインアップページ (V3)
 */
import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import './Auth.css';

export const SignupPage: React.FC = () => {
    const { signup } = useAuth();

    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [displayName, setDisplayName] = useState('');
    const [error, setError] = useState('');
    const [success, setSuccess] = useState(false);
    const [isLoading, setIsLoading] = useState(false);

    const validatePassword = (pwd: string): string[] => {
        const errors: string[] = [];
        if (pwd.length < 8) errors.push('8文字以上');
        if (!/[A-Z]/.test(pwd)) errors.push('大文字を含む');
        if (!/[a-z]/.test(pwd)) errors.push('小文字を含む');
        if (!/[0-9]/.test(pwd)) errors.push('数字を含む');
        return errors;
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');

        // パスワード確認
        if (password !== confirmPassword) {
            setError('パスワードが一致しません');
            return;
        }

        // パスワード強度チェック
        const pwdErrors = validatePassword(password);
        if (pwdErrors.length > 0) {
            setError(`パスワード要件: ${pwdErrors.join('、')}`);
            return;
        }

        setIsLoading(true);

        try {
            await signup(email, password, displayName || undefined);
            setSuccess(true);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'サインアップに失敗しました');
        } finally {
            setIsLoading(false);
        }
    };

    if (success) {
        return (
            <div className="auth-page">
                <div className="auth-container">
                    <div className="auth-success">
                        <div className="success-icon">✓</div>
                        <h2>登録完了</h2>
                        <p>確認メールを送信しました。メールを確認してアカウントを有効化してください。</p>
                        <Link to="/login" className="auth-button">ログインページへ</Link>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="auth-page">
            <div className="auth-container">
                <div className="auth-header">
                    <h1 className="auth-title">新規登録</h1>
                    <p className="auth-subtitle">アカウントを作成してLexFlowを始めましょう</p>
                </div>

                <form className="auth-form" onSubmit={handleSubmit}>
                    {error && <div className="auth-error">{error}</div>}

                    <div className="form-group">
                        <label htmlFor="displayName">表示名（任意）</label>
                        <input
                            type="text"
                            id="displayName"
                            value={displayName}
                            onChange={(e) => setDisplayName(e.target.value)}
                            placeholder="山田 太郎"
                        />
                    </div>

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
                            placeholder="8文字以上（大文字・小文字・数字）"
                            autoComplete="new-password"
                            required
                        />
                        <div className="password-requirements">
                            {validatePassword(password).length > 0 && password && (
                                <small className="requirement-hint">
                                    必要: {validatePassword(password).join('、')}
                                </small>
                            )}
                        </div>
                    </div>

                    <div className="form-group">
                        <label htmlFor="confirmPassword">パスワード確認</label>
                        <input
                            type="password"
                            id="confirmPassword"
                            value={confirmPassword}
                            onChange={(e) => setConfirmPassword(e.target.value)}
                            placeholder="もう一度入力"
                            autoComplete="new-password"
                            required
                        />
                    </div>

                    <button
                        type="submit"
                        className="auth-button"
                        disabled={isLoading}
                    >
                        {isLoading ? '登録中...' : '登録する'}
                    </button>
                </form>

                <div className="auth-footer">
                    <p>すでにアカウントをお持ちの方は</p>
                    <Link to="/login" className="auth-link">ログイン</Link>
                </div>
            </div>
        </div>
    );
};

export default SignupPage;
