/**
 * LexFlow Protocol - ワークスペース設定ページ (V3)
 */
import React, { useState, useEffect } from 'react';
import { useAuth, authFetch } from '../contexts/AuthContext';
import { API_BASE } from '../services/api';
import './WorkspaceSettings.css';

// const API_BASE = '/api/v1';

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

const PERMISSION_LABELS: Record<string, string> = {
    'workspace:view': 'ワークスペース閲覧',
    'workspace:edit': 'ワークスペース編集',
    'workspace:invite': 'メンバー招待',
    'workspace:remove_user': 'メンバー削除',
    'workspace:manage_roles': 'ロール管理',
    'contract:view': '契約書閲覧',
    'contract:create': '契約書作成',
    'contract:edit': '契約書編集',
    'contract:delete': '契約書削除',
    'contract:manage_acl': 'アクセス制御管理 (ACL)',
    'approval:view': '承認フロー閲覧',
    'approval:create': '承認フロー作成',
    'approval:create_flow': '承認フロー作成',
    'approval:request': '承認依頼の作成',
    'approval:approve': '契約書承認',
    'audit:view': '監査ログ閲覧'
};

const translatePermission = (key: string) => PERMISSION_LABELS[key] || key;

export const WorkspaceSettings: React.FC = () => {
    const { user } = useAuth();

    const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
    const [selectedWorkspace, setSelectedWorkspace] = useState<string | null>(null);
    const [roles, setRoles] = useState<Role[]>([]);
    const [members, setMembers] = useState<WorkspaceUser[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState('');

    // 新規ワークスペース作成
    const [showCreateModal, setShowCreateModal] = useState(false);
    const [newWorkspaceName, setNewWorkspaceName] = useState('');
    const [newWorkspaceOwner, setNewWorkspaceOwner] = useState('');
    const [newWorkspaceRole, setNewWorkspaceRole] = useState('Owner');

    // ユーザー招待
    const [showInviteModal, setShowInviteModal] = useState(false);
    const [inviteUserId, setInviteUserId] = useState('');
    const [inviteRoleId, setInviteRoleId] = useState('');
    const [inviteRoleName, setInviteRoleName] = useState('');

    const loadRoles = async (workspaceId: string) => {
        try {
            const res = await authFetch(`${API_BASE}/workspaces/${workspaceId}/roles`);
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
            const res = await authFetch(`${API_BASE}/workspaces/${workspaceId}/users`);
            if (res.ok) {
                const data = await res.json();
                setMembers(data);
            }
        } catch (err) {
            console.error('Failed to load members:', err);
        }
    };

    const loadWorkspaces = async () => {
        setIsLoading(true);
        try {
            const res = await authFetch(`${API_BASE}/workspaces`);
            if (res.ok) {
                const data = await res.json();
                setWorkspaces(data);
                if (data.length > 0 && !selectedWorkspace) {
                    setSelectedWorkspace(data[0].id);
                }
            }
        } catch (err) {
            console.error('Failed to load workspaces:', err);
            setError('ワークスペースの読み込みに失敗しました');
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        loadWorkspaces();
    }, []);

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
            const res = await authFetch(`${API_BASE}/workspaces`, {
                method: 'POST',
                body: JSON.stringify({
                    name: newWorkspaceName,
                    user_id: newWorkspaceOwner,
                    role_name: newWorkspaceRole
                })
            });

            if (!res.ok) throw new Error('ワークスペースの作成に失敗しました');

            const newWs = await res.json();
            setWorkspaces([...workspaces, newWs]);
            setSelectedWorkspace(newWs.id);
            setShowCreateModal(false);
            setNewWorkspaceName('');
            setNewWorkspaceOwner('');
            setNewWorkspaceRole('Owner');
        } catch (err) {
            setError(err instanceof Error ? err.message : 'エラーが発生しました');
        } finally {
            setIsLoading(false);
        }
    };

    const handleInviteUser = async () => {
        if (!selectedWorkspace || !inviteUserId || (!inviteRoleId && !inviteRoleName)) return;

        setIsLoading(true);
        setError('');

        try {
            const res = await authFetch(`${API_BASE}/workspaces/${selectedWorkspace}/users`, {
                method: 'POST',
                body: JSON.stringify({
                    user_id: inviteUserId,
                    role_id: (inviteRoleId && !inviteRoleId.startsWith('__')) ? inviteRoleId : undefined,
                    role_name: inviteRoleId.startsWith('__')
                        ? inviteRoleId.replace('__', '').charAt(0).toUpperCase() + inviteRoleId.slice(3)
                        : (inviteRoleId === '' ? inviteRoleName : undefined)
                })
            });

            if (!res.ok) {
                const errorData = await res.json();
                throw new Error(errorData.detail || 'ユーザーの招待に失敗しました');
            }

            await loadMembers(selectedWorkspace);
            setShowInviteModal(false);
            setInviteUserId('');
            setInviteRoleId('');
            setInviteRoleName('');
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
                        onClick={() => {
                            setNewWorkspaceOwner(user?.id || '');
                            setShowCreateModal(true);
                        }}
                    >
                        ➕ ワークスペースを新規作成
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
                                            ➕ メンバーを登録
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
                                                <ul className="role-permissions-list">
                                                    {role.permissions.map(p => (
                                                        <li key={p}>{translatePermission(p)}</li>
                                                    ))}
                                                </ul>
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
                            <div className="form-group">
                                <label>管理者（ユーザーID）</label>
                                <input
                                    type="text"
                                    value={newWorkspaceOwner}
                                    onChange={e => setNewWorkspaceOwner(e.target.value)}
                                    placeholder="ユーザーIDを入力"
                                />
                                <small style={{ color: '#64748b', marginTop: '0.5rem', display: 'block' }}>
                                    デフォルトであなたがオーナーとして登録されます
                                </small>
                            </div>
                            <div className="form-group">
                                <label>付与するロール</label>
                                <select
                                    value={newWorkspaceRole}
                                    onChange={e => setNewWorkspaceRole(e.target.value)}
                                >
                                    <option value="Owner">👑 Owner (全権限)</option>
                                    <option value="Admin">⚙️ Admin (管理)</option>
                                    <option value="Manager">📊 Manager (運用)</option>
                                    <option value="Member">👤 Member (一般)</option>
                                </select>
                            </div>
                            <div className="modal-actions">
                                <button className="cancel-btn" onClick={() => setShowCreateModal(false)}>
                                    キャンセル
                                </button>
                                <button
                                    className="submit-btn"
                                    onClick={handleCreateWorkspace}
                                    disabled={!newWorkspaceName.trim() || !newWorkspaceOwner.trim() || isLoading}
                                >
                                    {isLoading ? '作成中...' : 'ワークスペースを作成'}
                                </button>
                            </div>
                        </div>
                    </div>
                )}

                {/* ユーザー招待モーダル */}
                {showInviteModal && (
                    <div className="modal-overlay" onClick={() => setShowInviteModal(false)}>
                        <div className="modal-content" onClick={e => e.stopPropagation()}>
                            <div className="form-group">
                                <label>招待する名前（またはメールアドレス）</label>
                                <input
                                    type="text"
                                    value={inviteUserId}
                                    onChange={e => setInviteUserId(e.target.value)}
                                    placeholder="例: 田中 太郎, test@example.com など"
                                />
                                <small style={{ color: '#64748b', marginTop: '0.4rem', display: 'block' }}>
                                    システムに存在しない名前を入力した場合、自動的に新規登録されます
                                </small>
                            </div>
                            <div className="form-group">
                                <label>ロールを選択</label>
                                <select
                                    value={inviteRoleId}
                                    onChange={e => {
                                        const val = e.target.value;
                                        setInviteRoleId(val);

                                        if (val === '') {
                                            setInviteRoleName('');
                                        } else if (val.startsWith('__')) {
                                            const standardName = val.replace('__', '').charAt(0).toUpperCase() + val.slice(3);
                                            setInviteRoleName(standardName);
                                        } else {
                                            const role = roles.find(r => r.id === val);
                                            if (role) setInviteRoleName(role.name);
                                        }
                                    }}
                                >
                                    <optgroup label="カスタム入力を開始">
                                        <option value="">ロール名を自由に入力する...</option>
                                    </optgroup>

                                    {roles.length > 0 && (
                                        <optgroup label="作成済みのロール">
                                            {roles.map(role => (
                                                <option key={role.id} value={role.id}>
                                                    {getRoleIcon(role.name)} {role.name}
                                                </option>
                                            ))}
                                        </optgroup>
                                    )}

                                    <optgroup label="標準ロールから選ぶ">
                                        <option value="__owner">👑 Owner</option>
                                        <option value="__admin">⚙️ Admin</option>
                                        <option value="__manager">📊 Manager</option>
                                        <option value="__member">👤 Member</option>
                                    </optgroup>
                                </select>
                            </div>
                            {inviteRoleId === '' && (
                                <div className="form-group">
                                    <label>ロール名を入力</label>
                                    <input
                                        type="text"
                                        value={inviteRoleName}
                                        onChange={e => setInviteRoleName(e.target.value)}
                                        placeholder="例: ゲスト, 閲覧者 など"
                                    />
                                    <small style={{ color: '#64748b', marginTop: '0.4rem', display: 'block' }}>
                                        新しい役職名を入力すると、自動的に作成されます
                                    </small>
                                </div>
                            )}
                            <div className="modal-actions">
                                <button className="cancel-btn" onClick={() => setShowInviteModal(false)}>
                                    キャンセル
                                </button>
                                <button
                                    className="submit-btn"
                                    onClick={handleInviteUser}
                                    disabled={!inviteUserId || (inviteRoleId === '' && !inviteRoleName.trim()) || isLoading}
                                >
                                    {isLoading ? '登録中...' : 'メンバーを登録'}
                                </button>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div >
    );
};

export default WorkspaceSettings;
