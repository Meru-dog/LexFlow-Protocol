/**
 * LexFlow Protocol - ワークスペース設定ページ (V3)
 */
import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import './WorkspaceSettings.css';

const API_BASE = '/api/v1';

interface Role {
    id: string;
    name: string;
    is_custom: boolean;
    permissions: string[];
}

interface WorkspaceUser {
    id: string;
    user_id: string;
    role_id: string;
    role_name: string;
    status: string;
    joined_at: string | null;
}

interface Workspace {
    id: string;
    name: string;
    created_at: string;
}

export const WorkspaceSettings: React.FC = () => {
    const { /* user */ } = useAuth();  // TODO: Use for auth checks

    const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
    const [selectedWorkspace, setSelectedWorkspace] = useState<string | null>(null);
    const [roles, setRoles] = useState<Role[]>([]);
    const [members, setMembers] = useState<WorkspaceUser[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState('');

    // 新規ワークスペース作成
    const [showCreateModal, setShowCreateModal] = useState(false);
    const [newWorkspaceName, setNewWorkspaceName] = useState('');

    // ユーザー招待
    const [showInviteModal, setShowInviteModal] = useState(false);
    const [inviteUserId, setInviteUserId] = useState('');
    const [inviteRoleId, setInviteRoleId] = useState('');

    const loadRoles = async (workspaceId: string) => {
        try {
            const res = await fetch(`${API_BASE}/workspaces/${workspaceId}/roles`);
            if (res.ok) {
                const data = await res.json();
                setRoles(data);
            }
        } catch (err) {
            console.error('Failed to load roles:', err);
        }
    };

    const loadMembers = async (workspaceId: string) => {
        try {
            const res = await fetch(`${API_BASE}/workspaces/${workspaceId}/users`);
            if (res.ok) {
                const data = await res.json();
                setMembers(data);
            }
        } catch (err) {
            console.error('Failed to load members:', err);
        }
    };

    useEffect(() => {
        if (selectedWorkspace) {
            loadRoles(selectedWorkspace);
            loadMembers(selectedWorkspace);
        }
    }, [selectedWorkspace]);

    const handleCreateWorkspace = async () => {
        if (!newWorkspaceName.trim()) return;

        setIsLoading(true);
        setError('');

        try {
            const res = await fetch(`${API_BASE}/workspaces`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: newWorkspaceName })
            });

            if (!res.ok) throw new Error('ワークスペースの作成に失敗しました');

            const newWs = await res.json();
            setWorkspaces([...workspaces, newWs]);
            setSelectedWorkspace(newWs.id);
            setShowCreateModal(false);
            setNewWorkspaceName('');
        } catch (err) {
            setError(err instanceof Error ? err.message : 'エラーが発生しました');
        } finally {
            setIsLoading(false);
        }
    };

    const handleInviteUser = async () => {
        if (!selectedWorkspace || !inviteUserId || !inviteRoleId) return;

        setIsLoading(true);
        setError('');

        try {
            const res = await fetch(`${API_BASE}/workspaces/${selectedWorkspace}/users`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_id: inviteUserId, role_id: inviteRoleId })
            });

            if (!res.ok) throw new Error('ユーザーの招待に失敗しました');

            await loadMembers(selectedWorkspace);
            setShowInviteModal(false);
            setInviteUserId('');
            setInviteRoleId('');
        } catch (err) {
            setError(err instanceof Error ? err.message : 'エラーが発生しました');
        } finally {
            setIsLoading(false);
        }
    };

    const getRoleIcon = (roleName: string) => {
        const icons: Record<string, string> = {
            'Owner': '👑',
            'Admin': '⚙️',
            'Manager': '📊',
            'Member': '👤',
            'Approver': '✅',
            'Auditor': '🔍'
        };
        return icons[roleName] || '📋';
    };

    const getStatusBadge = (status: string) => {
        const styles: Record<string, { bg: string; color: string; text: string }> = {
            'invited': { bg: 'rgba(251, 191, 36, 0.1)', color: '#fbbf24', text: '招待中' },
            'active': { bg: 'rgba(16, 185, 129, 0.1)', color: '#10b981', text: '有効' },
            'removed': { bg: 'rgba(239, 68, 68, 0.1)', color: '#ef4444', text: '削除済' }
        };
        const style = styles[status] || styles['invited'];
        return (
            <span className="status-badge" style={{ background: style.bg, color: style.color }}>
                {style.text}
            </span>
        );
    };

    return (
        <div className="workspace-settings-page">
            <div className="workspace-settings-container">
                <div className="workspace-header">
                    <h1>🏢 ワークスペース設定</h1>
                    <button
                        className="create-workspace-btn"
                        onClick={() => setShowCreateModal(true)}
                    >
                        ➕ 新規作成
                    </button>
                </div>

                {error && <div className="workspace-error">{error}</div>}

                {workspaces.length === 0 ? (
                    <div className="empty-state">
                        <div className="empty-icon">🏗️</div>
                        <h3>ワークスペースがありません</h3>
                        <p>新しいワークスペースを作成して、チームメンバーを招待しましょう。</p>
                        <button
                            className="create-workspace-btn"
                            onClick={() => setShowCreateModal(true)}
                        >
                            ワークスペースを作成
                        </button>
                    </div>
                ) : (
                    <div className="workspace-content">
                        <div className="workspace-sidebar">
                            {workspaces.map(ws => (
                                <div
                                    key={ws.id}
                                    className={`workspace-item ${selectedWorkspace === ws.id ? 'active' : ''}`}
                                    onClick={() => setSelectedWorkspace(ws.id)}
                                >
                                    <span className="ws-icon">🏢</span>
                                    <span className="ws-name">{ws.name}</span>
                                </div>
                            ))}
                        </div>

                        {selectedWorkspace && (
                            <div className="workspace-detail">
                                <div className="section">
                                    <div className="section-header">
                                        <h2>👥 メンバー</h2>
                                        <button
                                            className="section-action-btn"
                                            onClick={() => setShowInviteModal(true)}
                                        >
                                            ➕ 招待
                                        </button>
                                    </div>

                                    <div className="members-list">
                                        {members.map(member => (
                                            <div key={member.id} className="member-item">
                                                <div className="member-info">
                                                    <div className="member-avatar">
                                                        {getRoleIcon(member.role_name)}
                                                    </div>
                                                    <div className="member-details">
                                                        <span className="member-id">{member.user_id.slice(0, 8)}...</span>
                                                        <span className="member-role">{member.role_name}</span>
                                                    </div>
                                                </div>
                                                {getStatusBadge(member.status)}
                                            </div>
                                        ))}
                                        {members.length === 0 && (
                                            <p className="no-data">メンバーがいません</p>
                                        )}
                                    </div>
                                </div>

                                <div className="section">
                                    <div className="section-header">
                                        <h2>🎭 ロール</h2>
                                    </div>

                                    <div className="roles-list">
                                        {roles.map(role => (
                                            <div key={role.id} className="role-item">
                                                <div className="role-header">
                                                    <span className="role-icon">{getRoleIcon(role.name)}</span>
                                                    <span className="role-name">{role.name}</span>
                                                    {role.is_custom && <span className="custom-badge">カスタム</span>}
                                                </div>
                                                <div className="role-permissions">
                                                    {role.permissions.slice(0, 3).map(p => (
                                                        <span key={p} className="permission-tag">{p}</span>
                                                    ))}
                                                    {role.permissions.length > 3 && (
                                                        <span className="permission-more">+{role.permissions.length - 3}</span>
                                                    )}
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>
                )}

                {/* 新規ワークスペース作成モーダル */}
                {showCreateModal && (
                    <div className="modal-overlay" onClick={() => setShowCreateModal(false)}>
                        <div className="modal-content" onClick={e => e.stopPropagation()}>
                            <h2>新規ワークスペース作成</h2>
                            <div className="form-group">
                                <label>ワークスペース名</label>
                                <input
                                    type="text"
                                    value={newWorkspaceName}
                                    onChange={e => setNewWorkspaceName(e.target.value)}
                                    placeholder="例: 法務部門"
                                />
                            </div>
                            <div className="modal-actions">
                                <button className="cancel-btn" onClick={() => setShowCreateModal(false)}>
                                    キャンセル
                                </button>
                                <button
                                    className="submit-btn"
                                    onClick={handleCreateWorkspace}
                                    disabled={!newWorkspaceName.trim() || isLoading}
                                >
                                    {isLoading ? '作成中...' : '作成'}
                                </button>
                            </div>
                        </div>
                    </div>
                )}

                {/* ユーザー招待モーダル */}
                {showInviteModal && (
                    <div className="modal-overlay" onClick={() => setShowInviteModal(false)}>
                        <div className="modal-content" onClick={e => e.stopPropagation()}>
                            <h2>ユーザー招待</h2>
                            <div className="form-group">
                                <label>ユーザーID</label>
                                <input
                                    type="text"
                                    value={inviteUserId}
                                    onChange={e => setInviteUserId(e.target.value)}
                                    placeholder="ユーザーIDを入力"
                                />
                            </div>
                            <div className="form-group">
                                <label>ロール</label>
                                <select
                                    value={inviteRoleId}
                                    onChange={e => setInviteRoleId(e.target.value)}
                                >
                                    <option value="">ロールを選択</option>
                                    {roles.map(role => (
                                        <option key={role.id} value={role.id}>
                                            {getRoleIcon(role.name)} {role.name}
                                        </option>
                                    ))}
                                </select>
                            </div>
                            <div className="modal-actions">
                                <button className="cancel-btn" onClick={() => setShowInviteModal(false)}>
                                    キャンセル
                                </button>
                                <button
                                    className="submit-btn"
                                    onClick={handleInviteUser}
                                    disabled={!inviteUserId || !inviteRoleId || isLoading}
                                >
                                    {isLoading ? '招待中...' : '招待'}
                                </button>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

export default WorkspaceSettings;
