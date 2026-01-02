/**
 * LexFlow Protocol - Protected Route Component (V3)
 * ユーザーが認証されているかを確認して、認証されていない場合はログインページにリダイレクトする
 */
import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

interface ProtectedRouteProps {
    children: React.ReactNode;
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children }) => {
    const { isAuthenticated, isLoading } = useAuth();

    if (isLoading) {
        return (
            <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                minHeight: '100vh',
                fontSize: '1.25rem',
                color: '#64748b'
            }}>
                読み込み中...
            </div>
        );
    }

    if (!isAuthenticated) {
        return <Navigate to="/login" replace />;
    }

    return <>{children}</>;
};
