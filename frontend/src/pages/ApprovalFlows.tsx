/**
 * LexFlow Protocol - 承認フロー管理ページ (V3)
 */
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth, authFetch } from '../contexts/AuthContext';
import { API_BASE } from '../services/api';
import './ApprovalFlows.css';

// const API_BASE = '/api/v1';

interface ApprovalFlow {
    id: string;
    workspace_id: string;
    name: string;
    description: string | null;
    stages: any[];
    is_active: boolean;
    created_at: string;
}

interface ApprovalRequest {
    id: string;
    contract_id: string;
    flow_id: string | null;
    status: string;
    due_at: string | null;
    message: string | null;
    created_by: string;
    created_at: string;
    tasks: ApprovalTask[];
}

interface ApprovalTask {
    id: string;
    stage: number;
    assignee_type: string;
    assignee_id: string;
    status: string;
    acted_at: string | null;
    comment: string | null;
    contract_title?: string;
}

interface WorkspaceUser {
    id: string;
    user_id: string;
    email: string | null;
    display_name: string | null;
    role_name: string;
}

export const ApprovalFlowsPage: React.FC = () => {
    const { /* user */ } = useAuth();  // TODO: Use for auth checks
    const navigate = useNavigate();

    const [activeTab, setActiveTab] = useState<'requests' | 'flows'>('requests');
    const [flows, setFlows] = useState<ApprovalFlow[]>([]);
    const [myRequests, setMyRequests] = useState<ApprovalRequest[]>([]);
    const [pendingTasks, setPendingTasks] = useState<any[]>([]); // タスクの型を拡張
    const [isLoading, setIsLoading] = useState(false);
    const [selectedRequest, setSelectedRequest] = useState<ApprovalRequest | null>(null);
    const [workspaces, setWorkspaces] = useState<any[]>([]);
    const [currentWorkspaceId, setCurrentWorkspaceId] = useState<string | null>(null);
    const [workspaceUsers, setWorkspaceUsers] = useState<WorkspaceUser[]>([]);

    // アクションモーダル
    const [showActionModal, setShowActionModal] = useState(false);
    const [actionType, setActionType] = useState<'approve' | 'reject' | 'return'>('approve');
    const [currentTaskId, setCurrentTaskId] = useState<string | null>(null);
    const [actionComment, setActionComment] = useState('');

    // フロー作成モーダル
    const [showCreateModal, setShowCreateModal] = useState(false);
    const [newFlowName, setNewFlowName] = useState('');
    const [newFlowDescription, setNewFlowDescription] = useState('');
    const [newFlowStages, setNewFlowStages] = useState<any[]>([
        { stage: 1, type: 'sequential', assignees: [{ type: 'user', id: '', order: 1 }] }
    ]);

    // フロー編集モーダル
    const [showEditModal, setShowEditModal] = useState(false);
    const [editingFlow, setEditingFlow] = useState<ApprovalFlow | null>(null);

    // フロー使用モーダル
    const [showUseModal, setShowUseModal] = useState(false);
    const [selectedFlowForUse, setSelectedFlowForUse] = useState<ApprovalFlow | null>(null);
    const [contracts, setContracts] = useState<any[]>([]);
    const [selectedContractId, setSelectedContractId] = useState<string>('');
    const [useMessage, setUseMessage] = useState('');

    useEffect(() => {
        const init = async () => {
            setIsLoading(true);
            try {
                // 1. ワークスペースを取得
                const wsRes = await authFetch(`${API_BASE}/workspaces`);
                if (wsRes.ok) {
                    const wsData = await wsRes.json();
                    setWorkspaces(wsData);
                    console.log('Loaded workspaces:', wsData); // Added log
                    if (wsData.length > 0) {
                        setCurrentWorkspaceId(wsData[0].id);
                        console.log('Set currentWorkspaceId to:', wsData[0].id); // Added log
                    } else {
                        console.warn('No workspaces found!'); // Added log for no workspaces
                    }
                }

                // 2. 自分の保留中タスクを取得（ワークスペースに関わらず）
                const tasksRes = await authFetch(`${API_BASE}/approvals/tasks?status=pending`);
                if (tasksRes.ok) {
                    const tasksData = await tasksRes.json();
                    setPendingTasks(tasksData);
                    console.log('Loaded pending tasks:', tasksData); // Added log
                } else {
                    console.error('Failed to load tasks:', await tasksRes.text());
                }
            } catch (err) {
                console.error('データの初期化に失敗しました:', err);
            } finally {
                setIsLoading(false);
            }
        };
        init();
    }, []);

    useEffect(() => {
        if (!currentWorkspaceId) return;

        const loadWorkspaceData = async () => {
            try {
                // フローテンプレート
                const flowsRes = await authFetch(`${API_BASE}/approvals/flows?workspace_id=${currentWorkspaceId}`);
                if (flowsRes.ok) {
                    const flowsData = await flowsRes.json();
                    setFlows(flowsData);
                }

                // すべてのリクエスト
                const reqsRes = await authFetch(`${API_BASE}/approvals/requests?workspace_id=${currentWorkspaceId}`);
                if (reqsRes.ok) {
                    const reqsData = await reqsRes.json();
                    setMyRequests(reqsData);
                    console.log('Loaded approval requests:', reqsData);
                } else {
                    console.error('Failed to load requests:', await reqsRes.text());
                }

                // ワークスペースユーザー
                const usersRes = await authFetch(`${API_BASE}/workspaces/${currentWorkspaceId}/users`);
                if (usersRes.ok) {
                    const usersData = await usersRes.json();
                    setWorkspaceUsers(usersData);
                }
            } catch (err) {
                console.error('ワークスペースデータの取得に失敗しました:', err);
            }
        };
        loadWorkspaceData();
    }, [currentWorkspaceId]);

    // ワークスペースの契約一覧を取得
    useEffect(() => {
        const loadContracts = async () => {
            if (!currentWorkspaceId) return;
            try {
                const res = await authFetch(`${API_BASE}/contracts/?workspace_id=${currentWorkspaceId}`);
                if (res.ok) {
                    const data = await res.json();
                    setContracts(data);
                }
            } catch (err) {
                console.error('契約一覧の取得に失敗しました:', err);
            }
        };
        if (showUseModal) {
            loadContracts();
        }
    }, [currentWorkspaceId, showUseModal]);

    const handleUseFlow = async () => {
        if (!selectedFlowForUse || !selectedContractId) return;

        setIsLoading(true);
        try {
            const res = await authFetch(`${API_BASE}/approvals/requests`, {
                method: 'POST',
                body: JSON.stringify({
                    contract_id: selectedContractId,
                    flow_id: selectedFlowForUse.id,
                    message: useMessage || null
                })
            });

            if (res.ok) {
                alert('承認依頼を作成しました！');
                setShowUseModal(false);
                setSelectedContractId('');
                setUseMessage('');
                setActiveTab('requests');

                // リクエスト一覧を更新
                const reqsRes = await authFetch(`${API_BASE}/approvals/requests?workspace_id=${currentWorkspaceId}`);
                if (reqsRes.ok) {
                    const reqsData = await reqsRes.json();
                    setMyRequests(reqsData);
                }
            } else {
                const error = await res.json();
                throw new Error(error.detail || '承認依頼の作成に失敗しました');
            }
        } catch (err) {
            alert(err instanceof Error ? err.message : 'エラーが発生しました');
        } finally {
            setIsLoading(false);
        }
    };

    const getStatusBadge = (status: string) => {
        const styles: Record<string, { bg: string; color: string; icon: string; text: string }> = {
            'pending': { bg: 'rgba(251, 191, 36, 0.1)', color: '#fbbf24', icon: '⏳', text: '承認待ち' },
            'approved': { bg: 'rgba(16, 185, 129, 0.1)', color: '#10b981', icon: '✓', text: '承認済み' },
            'rejected': { bg: 'rgba(239, 68, 68, 0.1)', color: '#ef4444', icon: '✗', text: '否認' },
            'returned': { bg: 'rgba(245, 158, 11, 0.1)', color: '#f59e0b', icon: '↩', text: '差戻し' },
            'expired': { bg: 'rgba(107, 114, 128, 0.1)', color: '#6b7280', icon: '⌛', text: '期限切れ' },
            'cancelled': { bg: 'rgba(107, 114, 128, 0.1)', color: '#6b7280', icon: '×', text: 'キャンセル' }
        };
        const style = styles[status] || styles['pending'];
        return (
            <span className="status-badge" style={{ background: style.bg, color: style.color }}>
                {style.icon} {style.text}
            </span>
        );
    };

    const handleAction = async (action: 'approve' | 'reject' | 'return') => {
        if (!currentTaskId) return;

        setIsLoading(true);
        try {
            const res = await authFetch(`${API_BASE}/approvals/tasks/${currentTaskId}/${action}`, {
                method: 'POST',
                body: JSON.stringify({ comment: actionComment })
            });

            if (!res.ok) {
                const error = await res.json();
                throw new Error(error.detail || 'アクションに失敗しました');
            }

            // リストを更新
            setShowActionModal(false);
            setActionComment('');
            setCurrentTaskId(null);

            // 選択中のリクエストを再読み込み
            if (selectedRequest) {
                const reqRes = await authFetch(`${API_BASE}/approvals/requests/${selectedRequest.id}`);
                if (reqRes.ok) {
                    const data = await reqRes.json();
                    setSelectedRequest(data);
                }
            }

            // 保留中タスクを更新
            const tasksRes = await authFetch(`${API_BASE}/approvals/tasks?status=pending`);
            if (tasksRes.ok) {
                const tasksData = await tasksRes.json();
                setPendingTasks(tasksData);
            }

            // すべてのリクエストを更新
            if (currentWorkspaceId) {
                const reqsRes = await authFetch(`${API_BASE}/approvals/requests?workspace_id=${currentWorkspaceId}`);
                if (reqsRes.ok) {
                    const reqsData = await reqsRes.json();
                    setMyRequests(reqsData);
                }
            }
        } catch (err) {
            alert(err instanceof Error ? err.message : 'エラーが発生しました');
        } finally {
            setIsLoading(false);
        }
    };

    const handleCreateFlow = async () => {
        if (!currentWorkspaceId) {
            if (confirm('ワークスペースが選択されていません。ワークスペース設定画面で作成しますか？')) {
                navigate('/workspaces');
            }
            return;
        }
        if (!newFlowName.trim()) {
            alert('フロー名を入力してください');
            return;
        }

        // バリデーション: 各ステージに少なくとも1人の承認者が設定されているか
        for (const stage of newFlowStages) {
            if (stage.assignees.some((a: any) => !a.id)) {
                alert('すべての承認者を設定してください');
                return;
            }
        }

        setIsLoading(true);
        try {
            const res = await authFetch(`${API_BASE}/approvals/flows?workspace_id=${currentWorkspaceId}`, {
                method: 'POST',
                body: JSON.stringify({
                    name: newFlowName,
                    description: newFlowDescription,
                    stages: newFlowStages
                })
            });

            if (!res.ok) {
                const error = await res.json();
                throw new Error(error.detail || 'フローの作成に失敗しました');
            }

            // 成功
            setShowCreateModal(false);
            setNewFlowName('');
            setNewFlowDescription('');
            setNewFlowStages([{ stage: 1, type: 'sequential', assignees: [{ type: 'user', id: '', order: 1 }] }]);

            // 再読み込み
            const flowsRes = await authFetch(`${API_BASE}/approvals/flows?workspace_id=${currentWorkspaceId}`);
            if (flowsRes.ok) {
                const flowsData = await flowsRes.json();
                setFlows(flowsData);
            }
        } catch (err) {
            alert(err instanceof Error ? err.message : 'エラーが発生しました');
        } finally {
            setIsLoading(false);
        }
    };

    const addStage = () => {
        setNewFlowStages([
            ...newFlowStages,
            { stage: newFlowStages.length + 1, type: 'sequential', assignees: [{ type: 'user', id: '', order: 1 }] }
        ]);
    };

    const removeStage = (index: number) => {
        const updated = newFlowStages.filter((_, i) => i !== index).map((s, i) => ({ ...s, stage: i + 1 }));
        setNewFlowStages(updated);
    };

    const addAssignee = (stageIndex: number) => {
        const updated = [...newFlowStages];
        updated[stageIndex].assignees.push({ type: 'user', id: '', order: updated[stageIndex].assignees.length + 1 });
        setNewFlowStages(updated);
    };

    const removeAssignee = (stageIndex: number, assigneeIndex: number) => {
        const updated = [...newFlowStages];
        updated[stageIndex].assignees = updated[stageIndex].assignees
            .filter((_: any, i: number) => i !== assigneeIndex)
            .map((a: any, i: number) => ({ ...a, order: i + 1 }));
        setNewFlowStages(updated);
    };

    const updateAssignee = (stageIndex: number, assigneeIndex: number, userId: string) => {
        const updated = [...newFlowStages];
        updated[stageIndex].assignees[assigneeIndex].id = userId;
        setNewFlowStages(updated);
    };

    const updateAssigneeType = (stageIndex: number, assigneeIndex: number, type: string) => {
        const updated = [...newFlowStages];
        updated[stageIndex].assignees[assigneeIndex].type = type;
        updated[stageIndex].assignees[assigneeIndex].id = ''; // IDをリセット
        setNewFlowStages(updated);
    };

    const openActionModal = (taskId: string, action: 'approve' | 'reject' | 'return') => {
        setCurrentTaskId(taskId);
        setActionType(action);
        setActionComment('');
        setShowActionModal(true);
    };

    const formatDate = (dateStr: string | null) => {
        if (!dateStr) return '未設定';
        return new Date(dateStr).toLocaleDateString('ja-JP', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    };

    return (
        <div className="approvals-page">
            <div className="approvals-container">
                <div className="approvals-header">
                    <h1>✅ 承認管理</h1>
                    <div className="header-actions">
                        {workspaces.length > 1 && (
                            <select
                                className="workspace-select"
                                value={currentWorkspaceId || ''}
                                onChange={(e) => setCurrentWorkspaceId(e.target.value)}
                            >
                                {workspaces.map(ws => (
                                    <option key={ws.id} value={ws.id}>{ws.name}</option>
                                ))}
                            </select>
                        )}
                        <div className="tab-buttons">
                            <button
                                className={`tab-btn ${activeTab === 'requests' ? 'active' : ''}`}
                                onClick={() => setActiveTab('requests')}
                            >
                                📋 承認リクエスト
                            </button>
                            <button
                                className={`tab-btn ${activeTab === 'flows' ? 'active' : ''}`}
                                onClick={() => setActiveTab('flows')}
                            >
                                🔄 フローテンプレート
                            </button>
                        </div>
                    </div>
                </div>

                {activeTab === 'requests' && (
                    <div className="requests-section">
                        <div className="subsection">
                            <h2>🔔 あなたの承認待ち</h2>
                            <div className="pending-tasks-grid">
                                {pendingTasks.length === 0 ? (
                                    <div className="empty-card">
                                        <span className="empty-icon">✨</span>
                                        <p>承認待ちのタスクはありません</p>
                                    </div>
                                ) : (
                                    pendingTasks.map(task => (
                                        <div key={task.id} className="pending-task-card">
                                            <div className="task-info">
                                                <span className="task-stage">ステージ {task.stage}</span>
                                                <span className="task-type">{task.assignee_type}</span>
                                            </div>
                                            <div className="task-contract">
                                                <span>📄 {task.contract_title || '不明な契約'}</span>
                                            </div>
                                            <div className="task-actions">
                                                <button
                                                    className="action-btn approve"
                                                    onClick={() => openActionModal(task.id, 'approve')}
                                                >
                                                    ✓ 承認
                                                </button>
                                                <button
                                                    className="action-btn reject"
                                                    onClick={() => openActionModal(task.id, 'reject')}
                                                >
                                                    ✗ 否認
                                                </button>
                                                <button
                                                    className="action-btn return"
                                                    onClick={() => openActionModal(task.id, 'return')}
                                                >
                                                    ↩ 差戻し
                                                </button>
                                            </div>
                                        </div>
                                    ))
                                )}
                            </div>
                        </div>

                        <div className="subsection">
                            <h2>📊 すべてのリクエスト</h2>
                            <div className="requests-grid">
                                {myRequests.length === 0 ? (
                                    <div className="empty-card">
                                        <span className="empty-icon">📭</span>
                                        <p>承認リクエストはありません</p>
                                    </div>
                                ) : (
                                    myRequests.map(request => (
                                        <div
                                            key={request.id}
                                            className={`request-card ${selectedRequest?.id === request.id ? 'selected' : ''}`}
                                            onClick={() => setSelectedRequest(request)}
                                        >
                                            <div className="request-header">
                                                <span className="request-id">#{request.id.slice(0, 8)}</span>
                                                {getStatusBadge(request.status)}
                                            </div>
                                            <div className="request-meta">
                                                <div className="meta-item">
                                                    <span className="meta-label">📄 契約ID:</span>
                                                    <span className="meta-value">{request.contract_id}</span>
                                                </div>
                                                {request.due_at && (
                                                    <div className="meta-item">
                                                        <span className="meta-label">📅 期限:</span>
                                                        <span className="meta-value">{formatDate(request.due_at)}</span>
                                                    </div>
                                                )}
                                                {request.message && (
                                                    <div className="meta-item">
                                                        <span className="meta-label">💬 メッセージ:</span>
                                                        <span className="meta-value">{request.message}</span>
                                                    </div>
                                                )}
                                            </div>
                                            <div className="request-progress">
                                                <span className="progress-label">承認ステージ:</span>
                                                <div className="task-badges">
                                                    {request.tasks.map((task, idx) => (
                                                        <span
                                                            key={idx}
                                                            className={`task-badge task-${task.status.toLowerCase()}`}
                                                            title={`ステージ ${task.stage}: ${task.status}`}
                                                        >
                                                            {task.stage}
                                                        </span>
                                                    ))}
                                                </div>
                                            </div>
                                            {request.tasks.some(t => t.comment) && (
                                                <div className="request-comments">
                                                    {request.tasks.filter(t => t.comment).map((task, idx) => (
                                                        <div key={idx} className="comment-bubble">
                                                            <span className="comment-meta">ステージ {task.stage}:</span>
                                                            <p className="comment-text">{task.comment}</p>
                                                        </div>
                                                    ))}
                                                </div>
                                            )}
                                        </div>
                                    ))
                                )}
                            </div>
                        </div>
                    </div>
                )}

                {activeTab === 'flows' && (
                    <div className="flows-section">
                        <div className="flows-grid-container">
                            {flows.length === 0 ? (
                                <div className="empty-card large centered">
                                    <span className="empty-icon">🔄</span>
                                    <h3>フローテンプレートがありません</h3>
                                    <p>承認フローテンプレートを作成して、承認プロセスを効率化しましょう。</p>
                                    <button className="create-flow-btn-large" onClick={() => {
                                        if (!currentWorkspaceId) {
                                            navigate('/workspaces');
                                        } else {
                                            setShowCreateModal(true);
                                        }
                                    }}>
                                        ➕ {currentWorkspaceId ? '新しく作成する' : 'ワークスペース設定へ'}
                                    </button>
                                </div>
                            ) : (
                                <>
                                    <div className="grid-header-actions">
                                        <button className="create-flow-btn-large" onClick={() => setShowCreateModal(true)}>
                                            ➕ フローを新しく作成する
                                        </button>
                                    </div>
                                    <div className="flows-grid">
                                        {flows.map(flow => (
                                            <div key={flow.id} className="flow-card">
                                                <div className="flow-header">
                                                    <h3>{flow.name}</h3>
                                                    {flow.is_active ? (
                                                        <span className="active-badge">有効</span>
                                                    ) : (
                                                        <span className="inactive-badge">無効</span>
                                                    )}
                                                </div>
                                                {flow.description && (
                                                    <p className="flow-description">{flow.description}</p>
                                                )}
                                                <div className="flow-stages">
                                                    {flow.stages.map((stage, idx) => (
                                                        <div key={idx} className="stage-indicator">
                                                            <span className="stage-num">{stage.stage}</span>
                                                            <span className="stage-type">
                                                                {stage.type === 'sequential' ? '順序' : '並列'}
                                                            </span>
                                                        </div>
                                                    ))}
                                                </div>
                                                <div className="flow-actions">
                                                    <button
                                                        className="flow-action-btn"
                                                        onClick={() => {
                                                            setEditingFlow(flow);
                                                            setShowEditModal(true);
                                                        }}
                                                    >
                                                        編集
                                                    </button>
                                                    <button
                                                        className="flow-action-btn"
                                                        onClick={() => {
                                                            setSelectedFlowForUse(flow);
                                                            setShowUseModal(true);
                                                        }}
                                                    >
                                                        使用
                                                    </button>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </>
                            )}
                        </div>
                    </div>
                )}
            </div>

            {/* アクションモーダル */}
            {showActionModal && (
                <div className="modal-overlay" onClick={() => setShowActionModal(false)}>
                    <div className="modal-content" onClick={e => e.stopPropagation()}>
                        <h2>
                            {actionType === 'approve' && '✓ 承認'}
                            {actionType === 'reject' && '✗ 否認'}
                            {actionType === 'return' && '↩ 差戻し'}
                        </h2>
                        <div className="form-group">
                            <label>コメント {(actionType === 'reject' || actionType === 'return') && '(必須)'}</label>
                            <textarea
                                value={actionComment}
                                onChange={e => setActionComment(e.target.value)}
                                placeholder={
                                    actionType === 'approve'
                                        ? 'コメントを入力（任意）'
                                        : '理由を入力してください'
                                }
                                rows={4}
                            />
                        </div>
                        <div className="modal-actions">
                            <button className="cancel-btn" onClick={() => setShowActionModal(false)}>
                                キャンセル
                            </button>
                            <button
                                className={`submit-btn ${actionType}`}
                                onClick={() => handleAction(actionType)}
                                disabled={
                                    isLoading ||
                                    ((actionType === 'reject' || actionType === 'return') && !actionComment.trim())
                                }
                            >
                                {isLoading ? '処理中...' : '確定'}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* フロー作成モーダル */}
            {showCreateModal && (
                <div className="modal-overlay" onClick={() => setShowCreateModal(false)}>
                    <div className="modal-content create-flow-modal" onClick={e => e.stopPropagation()}>
                        <h2>🔄 承認フローテンプレートを作成</h2>
                        <div className="form-group mt-6">
                            <label>フロー名</label>
                            <input
                                type="text"
                                className="input"
                                value={newFlowName}
                                onChange={e => setNewFlowName(e.target.value)}
                                placeholder="例: 支出承認フロー"
                            />
                        </div>
                        <div className="form-group">
                            <label>説明</label>
                            <textarea
                                className="input"
                                value={newFlowDescription}
                                onChange={e => setNewFlowDescription(e.target.value)}
                                placeholder="このフローの用途を説明してください"
                                rows={2}
                            />
                        </div>

                        <div className="stages-config">
                            <h3>🪜 ステージ設定</h3>
                            {newFlowStages.map((stage, sIdx) => (
                                <div key={sIdx} className="stage-config-item">
                                    <div className="stage-header">
                                        <h4>ステージ {stage.stage}</h4>
                                        {newFlowStages.length > 1 && (
                                            <button className="remove-stage-btn" onClick={() => removeStage(sIdx)}>削除</button>
                                        )}
                                    </div>
                                    <div className="stage-row">
                                        <label>タイプ</label>
                                        <select
                                            className="input"
                                            value={stage.type}
                                            onChange={e => {
                                                const updated = [...newFlowStages];
                                                updated[sIdx].type = e.target.value;
                                                setNewFlowStages(updated);
                                            }}
                                        >
                                            <option value="sequential">順序承認（全員の承認が必要）</option>
                                            <option value="parallel">並列承認（誰か一人の承認で次へ）</option>
                                        </select>
                                    </div>
                                    <div className="stage-row">
                                        <label>承認者</label>
                                        <div className="assignees-list">
                                            {stage.assignees.map((assignee: any, aIdx: number) => (
                                                <div key={aIdx} className="assignee-item">
                                                    <div className="assignee-row">
                                                        <select
                                                            className="assignee-type-select"
                                                            value={assignee.type}
                                                            onChange={e => updateAssigneeType(sIdx, aIdx, e.target.value)}
                                                        >
                                                            <option value="user">内部ユーザー</option>
                                                            <option value="external">外部（直接入力）</option>
                                                        </select>

                                                        {assignee.type === 'user' ? (
                                                            <select
                                                                className="assignee-select"
                                                                value={assignee.id}
                                                                onChange={e => updateAssignee(sIdx, aIdx, e.target.value)}
                                                            >
                                                                <option value="">承認者を選択...</option>
                                                                {workspaceUsers.map(u => (
                                                                    <option key={u.user_id} value={u.user_id}>
                                                                        {u.display_name || u.email} ({u.role_name})
                                                                    </option>
                                                                ))}
                                                            </select>
                                                        ) : (
                                                            <input
                                                                type="text"
                                                                className="assignee-input"
                                                                placeholder="ウォレットアドレスまたはIDを入力"
                                                                value={assignee.id}
                                                                onChange={e => updateAssignee(sIdx, aIdx, e.target.value)}
                                                            />
                                                        )}
                                                    </div>
                                                    {stage.assignees.length > 1 && (
                                                        <button className="remove-assignee-btn" onClick={() => removeAssignee(sIdx, aIdx)}>×</button>
                                                    )}
                                                </div>
                                            ))}
                                            <button className="add-btn-secondary" onClick={() => addAssignee(sIdx)}>
                                                ＋ 承認者を追加
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            ))}
                            <button className="add-stage-btn" onClick={addStage}>
                                ➕ 新しいステージを追加
                            </button>
                        </div>

                        <div className="modal-actions mt-8">
                            <button className="cancel-btn" onClick={() => setShowCreateModal(false)}>
                                キャンセル
                            </button>
                            <button
                                className="submit-btn approve"
                                onClick={handleCreateFlow}
                                disabled={isLoading || !newFlowName.trim()}
                            >
                                {isLoading ? '作成中...' : 'テンプレートを作成'}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* フロー編集モーダル */}
            {showEditModal && editingFlow && (
                <div className="modal-overlay" onClick={() => setShowEditModal(false)}>
                    <div className="modal-content" onClick={e => e.stopPropagation()}>
                        <h2>フローを編集</h2>
                        <div className="form-group">
                            <label>フロー名</label>
                            <input
                                type="text"
                                value={editingFlow.name}
                                onChange={e => setEditingFlow({ ...editingFlow, name: e.target.value })}
                                placeholder="例: 契約書承認フロー"
                            />
                        </div>
                        <div className="form-group">
                            <label>説明</label>
                            <textarea
                                value={editingFlow.description || ''}
                                onChange={e => setEditingFlow({ ...editingFlow, description: e.target.value })}
                                placeholder="フローの説明を入力"
                                rows={3}
                            />
                        </div>
                        <div className="modal-actions">
                            <button className="cancel-btn" onClick={() => setShowEditModal(false)}>
                                キャンセル
                            </button>
                            <button
                                className="submit-btn"
                                onClick={async () => {
                                    try {
                                        const res = await authFetch(`${API_BASE}/approvals/flows/${editingFlow.id}`, {
                                            method: 'PUT',
                                            body: JSON.stringify({
                                                name: editingFlow.name,
                                                description: editingFlow.description,
                                                is_active: editingFlow.is_active,
                                                stages: editingFlow.stages
                                            })
                                        });
                                        if (res.ok) {
                                            // Reload flows
                                            if (currentWorkspaceId) {
                                                const flowsRes = await authFetch(`${API_BASE}/approvals/flows?workspace_id=${currentWorkspaceId}`);
                                                if (flowsRes.ok) {
                                                    const flowsData = await flowsRes.json();
                                                    setFlows(flowsData);
                                                }
                                            }
                                            setShowEditModal(false);
                                            setEditingFlow(null);
                                        }
                                    } catch (err) {
                                        console.error('Failed to update flow:', err);
                                    }
                                }}
                            >
                                更新
                            </button>
                        </div>
                    </div>
                </div>
            )}
            {/* フロー使用モーダル */}
            {showUseModal && selectedFlowForUse && (
                <div className="modal-overlay" onClick={() => setShowUseModal(false)}>
                    <div className="modal-content" onClick={e => e.stopPropagation()}>
                        <h2>フローを使用: {selectedFlowForUse.name}</h2>
                        <div className="form-group">
                            <label>契約書を選択</label>
                            <select
                                className="input"
                                value={selectedContractId}
                                onChange={e => setSelectedContractId(e.target.value)}
                            >
                                <option value="">選択してください</option>
                                {contracts.map(c => (
                                    <option key={c.id} value={c.id}>
                                        {c.title} ({c.id.slice(0, 8)}...)
                                    </option>
                                ))}
                            </select>
                        </div>
                        <div className="form-group">
                            <label>メッセージ（任意）</label>
                            <textarea
                                className="input"
                                value={useMessage}
                                onChange={e => setUseMessage(e.target.value)}
                                placeholder="承認者へのメッセージを入力"
                                rows={3}
                            />
                        </div>
                        <div className="modal-actions">
                            <button className="cancel-btn" onClick={() => setShowUseModal(false)}>
                                キャンセル
                            </button>
                            <button
                                className="submit-btn"
                                onClick={handleUseFlow}
                                disabled={isLoading || !selectedContractId}
                            >
                                {isLoading ? '作成中...' : '承認依頼を作成'}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default ApprovalFlowsPage;
