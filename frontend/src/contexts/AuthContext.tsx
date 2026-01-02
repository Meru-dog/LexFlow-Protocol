import React, { createContext, useContext, useState, useEffect, type ReactNode } from 'react';

// ===== 型定義 =====
interface User {
    id: string;
    email: string;
    displayName?: string;
    wallets: string[];
}

interface AuthContextType {
    user: User | null;
    isAuthenticated: boolean;
    isLoading: boolean;
    login: (email: string, password: string) => Promise<void>;
    signup: (email: string, password: string, displayName?: string) => Promise<void>;
    logout: () => void;
    refreshToken: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// ===== APIベースURL =====
const API_BASE = '/api/v1';

// ===== トークン管理 =====
const getAccessToken = () => localStorage.getItem('access_token');
const getRefreshToken = () => localStorage.getItem('refresh_token');
const setTokens = (accessToken: string, refreshToken: string) => {
    localStorage.setItem('access_token', accessToken);
    localStorage.setItem('refresh_token', refreshToken);
};
const clearTokens = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
};

// ===== AuthProvider =====
export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
    const [user, setUser] = useState<User | null>(null);
    const [isLoading, setIsLoading] = useState(true);

    // 初期化時にトークンをチェック
    useEffect(() => {
        const initAuth = async () => {
            const token = getAccessToken();
            if (token) {
                try {
                    // JWTをデコードしてユーザー情報を取得（簡易版）
                    const payload = JSON.parse(atob(token.split('.')[1]));
                    setUser({
                        id: payload.sub,
                        email: payload.email,
                        wallets: []
                    });
                } catch {
                    clearTokens();
                }
            }
            setIsLoading(false);
        };
        initAuth();
    }, []);

    const login = async (email: string, password: string) => {
        const response = await fetch(`${API_BASE}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'ログインに失敗しました');
        }

        const data = await response.json();
        setTokens(data.access_token, data.refresh_token);
        setUser({
            id: data.user_id,
            email: data.email,
            wallets: []
        });
    };

    const signup = async (email: string, password: string, displayName?: string) => {
        const response = await fetch(`${API_BASE}/auth/signup`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password, display_name: displayName })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'サインアップに失敗しました');
        }

        // サインアップ後は自動ログインせず、メール確認を促す
        return;
    };

    const logout = () => {
        clearTokens();
        setUser(null);
    };

    const refreshToken = async () => {
        const token = getRefreshToken();
        if (!token) {
            logout();
            return;
        }

        try {
            const response = await fetch(`${API_BASE}/auth/token/refresh`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ refresh_token: token })
            });

            if (!response.ok) {
                logout();
                return;
            }

            const data = await response.json();
            setTokens(data.access_token, data.refresh_token);
        } catch {
            logout();
        }
    };

    return (
        <AuthContext.Provider value={{
            user,
            isAuthenticated: !!user,
            isLoading,
            login,
            signup,
            logout,
            refreshToken
        }}>
            {children}
        </AuthContext.Provider>
    );
};

// ===== useAuth フック =====
export const useAuth = (): AuthContextType => {
    const context = useContext(AuthContext);
    if (context === undefined) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
};

// ===== 認証済みAPI呼び出しヘルパー =====
export const authFetch = async (url: string, options: RequestInit = {}): Promise<Response> => {
    const token = getAccessToken();
    const headers = {
        ...options.headers,
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
    };

    return fetch(url, { ...options, headers });
};
