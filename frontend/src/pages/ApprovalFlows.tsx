/**
 * LexFlow Protocol - 承認フロー管理ページ (V3)
 */
import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import './ApprovalFlows.css';

const API_BASE = '/api/v1';

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
}

export const ApprovalFlowsPage: React.FC = () => {
    const { /* user */ } = useAuth();  // TODO: Use for auth checks

    const [activeTab, setActiveTab] = useState<'requests' | 'flows'>('requests');
    const [flows, _setFlows] = useState<ApprovalFlow[]>([]);
    const [myRequests, _setMyRequests] = useState<ApprovalRequest[]>([]);
    const [pendingTasks, _setPendingTasks] = useState<ApprovalTask[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [selectedRequest, setSelectedRequest] = useState<ApprovalRequest | null>(null);

    // アクションモーダル
    const [showActionModal, setShowActionModal] = useState(false);
    const [actionType, setActionType] = useState<'approve' | 'reject' | 'return'>('approve');
    const [currentTaskId, setCurrentTaskId] = useState<string | null>(null);
    const [actionComment, setActionComment] = useState('');

    // TODO: Call this in useEffect when workspace context is available
    // const _loadFlows = async (workspaceId: string) => {
    //     try {
    //         const res = await fetch(`${API_BASE}/approvals/flows?workspace_id=${workspaceId}`);
    //         if (res.ok) {
    //             const data = await res.json();
    //             setFlows(data);
    //         }
    //     } catch (err) {
    //         console.error('承認フローの取得に失敗しました。', err);
    //     }
    // };

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
            const res = await fetch(`${API_BASE}/approvals/tasks/${currentTaskId}/${action}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
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
                const reqRes = await fetch(`${API_BASE}/approvals/requests/${selectedRequest.id}`);
                if (reqRes.ok) {
                    const data = await reqRes.json();
                    setSelectedRequest(data);
                }
            }
        } catch (err) {
            alert(err instanceof Error ? err.message : 'エラーが発生しました');
        } finally {
            setIsLoading(false);
        }
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
                            <div className="requests-list">
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
                                                <span>📄 契約: {request.contract_id.slice(0, 8)}...</span>
                                                <span>📅 期限: {formatDate(request.due_at)}</span>
                                            </div>
                                            <div className="request-progress">
                                                {request.tasks.map((task, idx) => (
                                                    <div
                                                        key={task.id}
                                                        className={`progress-step ${task.status}`}
                                                        title={`ステージ ${task.stage}: ${task.status}`}
                                                    >
                                                        {idx + 1}
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    ))
                                )}
                            </div>
                        </div>
                    </div>
                )}

                {activeTab === 'flows' && (
                    <div className="flows-section">
                        <div className="flows-grid">
                            {flows.length === 0 ? (
                                <div className="empty-card large">
                                    <span className="empty-icon">🔄</span>
                                    <h3>フローテンプレートがありません</h3>
                                    <p>承認フローテンプレートを作成して、承認プロセスを効率化しましょう。</p>
                                    <button className="create-flow-btn">
                                        ➕ フローを作成
                                    </button>
                                </div>
                            ) : (
                                flows.map(flow => (
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
                                            <button className="flow-action-btn">編集</button>
                                            <button className="flow-action-btn">使用</button>
                                        </div>
                                    </div>
                                ))
                            )}
                        </div>
                    </div>
                )}

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
            </div>
        </div>
    );
};

export default ApprovalFlowsPage;
