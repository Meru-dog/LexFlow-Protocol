import React, { useState, useEffect } from 'react';
import './AuditLog.css';
import { api } from '../services/api';

interface AuditEvent {
    id: string;
    type: string;
    actor_id: string | null;
    actor_wallet: string | null;
    workspace_id: string | null;
    contract_id: string | null;
    resource_id: string | null;
    resource_type: string | null;
    detail: any;
    prev_hash: string | null;
    hash: string;
    created_at: string;
}

interface EventType {
    key: string;
    name: string;
}

const AuditLog: React.FC = () => {
    const [events, setEvents] = useState<AuditEvent[]>([]);
    const [eventTypes, setEventTypes] = useState<EventType[]>([]);
    const [loading, setLoading] = useState(false);
    const [verifying, setVerifying] = useState(false);
    const [exporting, setExporting] = useState(false);

    // Filters
    const [eventType, setEventType] = useState('');
    const [fromDate, setFromDate] = useState('');
    const [toDate, setToDate] = useState('');
    const [actorId, setActorId] = useState('');
    const [contractId, setContractId] = useState('');

    // Pagination
    const [page, setPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);
    const [total, setTotal] = useState(0);

    // Modals
    const [selectedEvent, setSelectedEvent] = useState<AuditEvent | null>(null);
    const [verifyResult, setVerifyResult] = useState<any>(null);
    const [exportMenuOpen, setExportMenuOpen] = useState(false);

    useEffect(() => {
        loadEventTypes();
        loadEvents();
    }, [page, eventType, fromDate, toDate, actorId, contractId]);

    useEffect(() => {
        // クリック外側で閉じる
        const handleClickOutside = () => setExportMenuOpen(false);
        if (exportMenuOpen) {
            document.addEventListener('click', handleClickOutside);
            return () => document.removeEventListener('click', handleClickOutside);
        }
    }, [exportMenuOpen]);

    const loadEventTypes = async () => {
        try {
            const res: any = await api.getAuditEventTypes();
            setEventTypes(res.types || []);
        } catch (error) {
            console.error('イベントタイプを取得できませんでした:', error);
        }
    };

    const loadEvents = async () => {
        setLoading(true);
        try {
            const params: any = { page, page_size: 50 };
            if (eventType) params.event_type = eventType;
            if (fromDate) params.from_date = new Date(fromDate).toISOString();
            if (toDate) params.to_date = new Date(toDate).toISOString();
            if (actorId) params.actor_id = actorId;
            if (contractId) params.contract_id = contractId;

            const res: any = await api.getAuditEvents(params);
            setEvents(res.events || []);
            setTotal(res.total || 0);
            setTotalPages(Math.ceil((res.total || 0) / 50));
        } catch (error) {
            console.error('監査証跡を取得できませんでした:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleVerifyIntegrity = async () => {
        setVerifying(true);
        try {
            const res: any = await api.verifyAuditChain({ limit: 1000 });
            setVerifyResult(res);
        } catch (error: any) {
            alert('検証に失敗しました: ' + (error.message || 'Unknown error'));
        } finally {
            setVerifying(false);
        }
    };

    const handleExport = async (format: 'csv' | 'json') => {
        setExporting(true);
        try {
            const params: any = { format };
            if (eventType) params.event_type = eventType;
            if (fromDate) params.from_date = new Date(fromDate).toISOString();
            if (toDate) params.to_date = new Date(toDate).toISOString();
            if (actorId) params.actor_id = actorId;
            if (contractId) params.contract_id = contractId;

            const blob = await api.exportAuditEvents(format, params);

            // ダウンロード
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `audit_export_${new Date().toISOString().split('T')[0]}.${format}`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
        } catch (error: any) {
            alert('エクスポートに失敗しました: ' + (error.response?.data?.detail || error.message));
        } finally {
            setExporting(false);
        }
    };

    const resetFilters = () => {
        setEventType('');
        setFromDate('');
        setToDate('');
        setActorId('');
        setContractId('');
        setPage(1);
    };

    const formatDate = (dateStr: string) => {
        return new Date(dateStr).toLocaleString('ja-JP');
    };

    const shortId = (id: string | null) => {
        if (!id) return '-';
        return id.length > 8 ? id.substring(0, 8) + '...' : id;
    };

    return (
        <div className="audit-log-page">
            <div className="audit-header">
                <h1>📋 監査証跡 (Audit Log)</h1>
                <div className="header-actions">
                    <button
                        onClick={handleVerifyIntegrity}
                        disabled={verifying}
                        className="btn-verify"
                    >
                        {verifying ? '検証中...' : '✓ Verify Integrity'}
                    </button>
                    <div className={`export-dropdown ${exportMenuOpen ? 'active' : ''}`}>
                        <button
                            disabled={exporting}
                            className="btn-export"
                            onClick={(e) => {
                                e.stopPropagation();
                                setExportMenuOpen(!exportMenuOpen);
                            }}
                        >
                            {exporting ? 'エクスポート中...' : '↓ Export'}
                        </button>
                        <div className="export-menu">
                            <button onClick={(e) => {
                                e.stopPropagation();
                                handleExport('csv');
                                setExportMenuOpen(false);
                            }}>CSV形式</button>
                            <button onClick={(e) => {
                                e.stopPropagation();
                                handleExport('json');
                                setExportMenuOpen(false);
                            }}>JSON形式</button>
                        </div>
                    </div>
                </div>
            </div>

            <div className="audit-filters">
                <div className="filter-row">
                    <div className="filter-group">
                        <label>イベントタイプ:</label>
                        <select value={eventType} onChange={(e) => setEventType(e.target.value)}>
                            <option value="">すべて</option>
                            {eventTypes.map(et => (
                                <option key={et.key} value={et.key}>{et.name}</option>
                            ))}
                        </select>
                    </div>

                    <div className="filter-group">
                        <label>開始日:</label>
                        <input
                            type="date"
                            value={fromDate}
                            onChange={(e) => setFromDate(e.target.value)}
                        />
                    </div>

                    <div className="filter-group">
                        <label>終了日:</label>
                        <input
                            type="date"
                            value={toDate}
                            onChange={(e) => setToDate(e.target.value)}
                        />
                    </div>

                    <div className="filter-group">
                        <label>Actor ID:</label>
                        <input
                            type="text"
                            placeholder="User ID..."
                            value={actorId}
                            onChange={(e) => setActorId(e.target.value)}
                        />
                    </div>

                    <div className="filter-group">
                        <label>Contract ID:</label>
                        <input
                            type="text"
                            placeholder="Contract ID..."
                            value={contractId}
                            onChange={(e) => setContractId(e.target.value)}
                        />
                    </div>

                    <button onClick={resetFilters} className="btn-reset">リセット</button>
                </div>
            </div>

            <div className="audit-stats">
                <span>総件数: {total}件</span>
                <span>ページ: {page} / {totalPages}</span>
            </div>

            {loading ? (
                <div className="loading">読み込み中...</div>
            ) : events.length === 0 ? (
                <div className="no-events">監査イベントがありません</div>
            ) : (
                <div className="events-table-container">
                    <table className="events-table">
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Type</th>
                                <th>Actor</th>
                                <th>Resource</th>
                                <th>Hash</th>
                                <th>Timestamp</th>
                                <th>詳細</th>
                            </tr>
                        </thead>
                        <tbody>
                            {events.map(event => (
                                <tr key={event.id}>
                                    <td className="id-cell" title={event.id}>{shortId(event.id)}</td>
                                    <td className="type-cell">
                                        <span className="type-badge">{event.type.replace(/\./g, ': ')}</span>
                                    </td>
                                    <td className="actor-cell" title={event.actor_id || ''}>
                                        {shortId(event.actor_id)}
                                    </td>
                                    <td className="resource-cell">
                                        {event.resource_type ? `${event.resource_type}: ${shortId(event.resource_id)}` : '-'}
                                    </td>
                                    <td className="hash-cell" title={event.hash}>
                                        {shortId(event.hash)}
                                    </td>
                                    <td className="time-cell">{formatDate(event.created_at)}</td>
                                    <td>
                                        <button
                                            onClick={() => setSelectedEvent(event)}
                                            className="btn-detail"
                                        >
                                            詳細
                                        </button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}

            <div className="pagination">
                <button
                    onClick={() => setPage(p => Math.max(1, p - 1))}
                    disabled={page === 1}
                >
                    前へ
                </button>
                <span>ページ {page} / {totalPages}</span>
                <button
                    onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                    disabled={page === totalPages}
                >
                    次へ
                </button>
            </div>

            {/* Event Detail Modal */}
            {selectedEvent && (
                <div className="modal-overlay" onClick={() => setSelectedEvent(null)}>
                    <div className="modal-content" onClick={(e) => e.stopPropagation()}>
                        <h2>監査イベント詳細</h2>
                        <div className="event-detail">
                            <p><strong>ID:</strong> {selectedEvent.id}</p>
                            <p><strong>Type:</strong> {selectedEvent.type}</p>
                            <p><strong>Actor ID:</strong> {selectedEvent.actor_id || '-'}</p>
                            <p><strong>Actor Wallet:</strong> {selectedEvent.actor_wallet || '-'}</p>
                            <p><strong>Workspace ID:</strong> {selectedEvent.workspace_id || '-'}</p>
                            <p><strong>Contract ID:</strong> {selectedEvent.contract_id || '-'}</p>
                            <p><strong>Resource ID:</strong> {selectedEvent.resource_id || '-'}</p>
                            <p><strong>Resource Type:</strong> {selectedEvent.resource_type || '-'}</p>
                            <p><strong>Hash:</strong> <code>{selectedEvent.hash}</code></p>
                            <p><strong>Prev Hash:</strong> <code>{selectedEvent.prev_hash || '-'}</code></p>
                            <p><strong>Created At:</strong> {formatDate(selectedEvent.created_at)}</p>
                            {selectedEvent.detail && (
                                <div>
                                    <strong>Detail:</strong>
                                    <pre>{JSON.stringify(selectedEvent.detail, null, 2)}</pre>
                                </div>
                            )}
                        </div>
                        <button onClick={() => setSelectedEvent(null)} className="btn-close">閉じる</button>
                    </div>
                </div>
            )}

            {/* Verify Result Modal */}
            {verifyResult && (
                <div className="modal-overlay" onClick={() => setVerifyResult(null)}>
                    <div className="modal-content verification-modal" onClick={(e) => e.stopPropagation()}>
                        <h2>ハッシュチェーン整合性検証結果</h2>
                        <div className={`verify-result ${verifyResult.valid ? 'valid' : 'invalid'}`}>
                            {verifyResult.valid ? (
                                <div className="success-icon">✓</div>
                            ) : (
                                <div className="error-icon">✗</div>
                            )}
                            <h3>{verifyResult.message}</h3>
                            <p>検証件数: {verifyResult.checked_count}件</p>
                            {verifyResult.first_invalid_id && (
                                <p className="error-detail">
                                    最初の不整合イベント: {verifyResult.first_invalid_id}
                                </p>
                            )}
                        </div>
                        <button onClick={() => setVerifyResult(null)} className="btn-close">閉じる</button>
                    </div>
                </div>
            )}
        </div>
    );
};

export default AuditLog;
