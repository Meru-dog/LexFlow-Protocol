import React, { useState, useEffect } from 'react';
import './Notifications.css';
import { api } from '../services/api';

interface Notification {
    id: string;
    channel: string;
    recipient: string;
    subject: string | null;
    payload: any;
    status: string;
    error: string | null;
    sent_at: string | null;
    created_at: string;
}

const Notifications: React.FC = () => {
    const [notifications, setNotifications] = useState<Notification[]>([]);
    const [loading, setLoading] = useState(false);
    const [statusFilter, setStatusFilter] = useState('');
    const [channelFilter, setChannelFilter] = useState('');
    const [selectedNotification, setSelectedNotification] = useState<Notification | null>(null);

    useEffect(() => {
        loadNotifications();
    }, [statusFilter, channelFilter]);

    const loadNotifications = async () => {
        setLoading(true);
        try {
            const params: any = {};
            if (statusFilter) params.status = statusFilter;
            if (channelFilter) params.channel = channelFilter;

            const res: any = await api.getNotifications(params);
            setNotifications(res.notifications || []);
        } catch (error) {
            console.error('通知履歴を取得できませんでした:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleResend = async (notificationId: string) => {
        if (!confirm('この通知を再送信しますか？')) return;

        try {
            await api.resendNotification(notificationId);
            alert('通知を再送信しました');
            loadNotifications();
        } catch (error: any) {
            alert('再送信に失敗しました: ' + (error.message || 'Unknown error'));
        }
    };

    const formatDate = (dateStr: string) => {
        return new Date(dateStr).toLocaleString('ja-JP');
    };

    const getStatusBadge = (status: string) => {
        const statusMap: Record<string, { label: string; className: string }> = {
            'PENDING': { label: '送信待ち', className: 'status-pending' },
            'SENT': { label: '送信済み', className: 'status-sent' },
            'FAILED': { label: '失敗', className: 'status-failed' },
        };
        const info = statusMap[status] || { label: status, className: 'status-unknown' };
        return <span className={`status-badge ${info.className}`}>{info.label}</span>;
    };

    const getChannelIcon = (channel: string) => {
        return channel === 'email' ? '📧' : channel === 'slack' ? '💬' : '📬';
    };

    const stats = {
        total: notifications.length,
        sent: notifications.filter(n => n.status === 'SENT').length,
        failed: notifications.filter(n => n.status === 'FAILED').length,
        pending: notifications.filter(n => n.status === 'PENDING').length,
    };

    return (
        <div className="notifications-page">
            <div className="notifications-header">
                <h1>📬 通知履歴 (Notifications)</h1>
                <button onClick={loadNotifications} className="btn-refresh">
                    🔄 更新
                </button>
            </div>

            <div className="notifications-stats">
                <div className="stat-card">
                    <div className="stat-value">{stats.total}</div>
                    <div className="stat-label">総通知数</div>
                </div>
                <div className="stat-card success">
                    <div className="stat-value">{stats.sent}</div>
                    <div className="stat-label">送信成功</div>
                </div>
                <div className="stat-card failed">
                    <div className="stat-value">{stats.failed}</div>
                    <div className="stat-label">送信失敗</div>
                </div>
                <div className="stat-card pending">
                    <div className="stat-value">{stats.pending}</div>
                    <div className="stat-label">送信待ち</div>
                </div>
            </div>

            <div className="notifications-filters">
                <div className="filter-group">
                    <label>ステータス:</label>
                    <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
                        <option value="">すべて</option>
                        <option value="SENT">送信済み</option>
                        <option value="FAILED">失敗</option>
                        <option value="PENDING">送信待ち</option>
                    </select>
                </div>

                <div className="filter-group">
                    <label>チャネル:</label>
                    <select value={channelFilter} onChange={(e) => setChannelFilter(e.target.value)}>
                        <option value="">すべて</option>
                        <option value="email">Email</option>
                        <option value="slack">Slack</option>
                    </select>
                </div>

                <button onClick={() => { setStatusFilter(''); setChannelFilter(''); }} className="btn-reset">
                    リセット
                </button>
            </div>

            {loading ? (
                <div className="loading">読み込み中...</div>
            ) : notifications.length === 0 ? (
                <div className="no-notifications">通知履歴がありません</div>
            ) : (
                <div className="notifications-list">
                    {notifications.map(notification => (
                        <div key={notification.id} className="notification-card">
                            <div className="notification-icon">
                                {getChannelIcon(notification.channel)}
                            </div>
                            <div className="notification-content">
                                <div className="notification-header-row">
                                    <h3 className="notification-subject">
                                        {notification.subject || '(件名なし)'}
                                    </h3>
                                    {getStatusBadge(notification.status)}
                                </div>
                                <div className="notification-meta">
                                    <span className="notification-recipient">
                                        宛先: {notification.recipient}
                                    </span>
                                    <span className="notification-time">
                                        {notification.sent_at
                                            ? `送信: ${formatDate(notification.sent_at)}`
                                            : `作成: ${formatDate(notification.created_at)}`
                                        }
                                    </span>
                                </div>
                                {notification.error && (
                                    <div className="notification-error">
                                        エラー: {notification.error}
                                    </div>
                                )}
                            </div>
                            <div className="notification-actions">
                                <button
                                    onClick={() => setSelectedNotification(notification)}
                                    className="btn-detail"
                                >
                                    詳細
                                </button>
                                {notification.status === 'FAILED' && (
                                    <button
                                        onClick={() => handleResend(notification.id)}
                                        className="btn-resend"
                                    >
                                        再送
                                    </button>
                                )}
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {/* Detail Modal */}
            {selectedNotification && (
                <div className="modal-overlay" onClick={() => setSelectedNotification(null)}>
                    <div className="modal-content" onClick={(e) => e.stopPropagation()}>
                        <h2>通知詳細</h2>
                        <div className="notification-detail">
                            <p><strong>ID:</strong> {selectedNotification.id}</p>
                            <p><strong>チャネル:</strong> {selectedNotification.channel}</p>
                            <p><strong>宛先:</strong> {selectedNotification.recipient}</p>
                            <p><strong>件名:</strong> {selectedNotification.subject || '-'}</p>
                            <p><strong>ステータス:</strong> {selectedNotification.status}</p>
                            <p><strong>作成日時:</strong> {formatDate(selectedNotification.created_at)}</p>
                            {selectedNotification.sent_at && (
                                <p><strong>送信日時:</strong> {formatDate(selectedNotification.sent_at)}</p>
                            )}
                            {selectedNotification.error && (
                                <p className="error-text">
                                    <strong>エラーメッセージ:</strong> {selectedNotification.error}
                                </p>
                            )}
                            {selectedNotification.payload && (
                                <div>
                                    <strong>ペイロード:</strong>
                                    <pre>{JSON.stringify(selectedNotification.payload, null, 2)}</pre>
                                </div>
                            )}
                        </div>
                        <button onClick={() => setSelectedNotification(null)} className="btn-close">
                            閉じる
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
};

export default Notifications;
