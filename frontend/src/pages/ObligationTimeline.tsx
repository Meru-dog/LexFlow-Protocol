import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Calendar, Clock, CheckCircle, AlertCircle, XCircle, FileText, Edit2, Play, Check } from 'lucide-react';
import { api } from '../services/api';
import type { Obligation, ObligationType, RiskLevel, ObligationStatus } from '../types';
import { PaymentModal } from '../components/PaymentModal';
import './ObligationTimeline.css';

/**
 * 義務タイムラインビューコンポーネント
 * 特定の契約に紐づく義務を期限順に一覧表示
 */
const ObligationTimeline: React.FC = () => {
    const { contractId } = useParams<{ contractId: string }>();
    const [obligations, setObligations] = useState<Obligation[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [filter, setFilter] = useState<{
        type?: ObligationType;
        status?: ObligationStatus;
        risk?: RiskLevel;
    }>({});

    // 編集モーダル状態
    const [editingObligation, setEditingObligation] = useState<Obligation | null>(null);
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [isProcessing, setIsProcessing] = useState(false);

    // F8: x402 支払い状態
    const [showPaymentModal, setShowPaymentModal] = useState(false);
    const [paymentInfo, setPaymentInfo] = useState<any>(null);

    const [statusMessage, setStatusMessage] = useState<string | null>(null);

    // 義務データの取得
    useEffect(() => {
        if (contractId) {
            loadObligations();
        }
    }, [contractId]);

    const loadObligations = async () => {
        try {
            setLoading(true);
            const data = await api.getObligationsByContract(contractId!) as Obligation[];
            setObligations(data);
            setError(null);
        } catch (err: any) {
            setError(err.message || '義務の取得に失敗しました');
        } finally {
            setLoading(false);
        }
    };

    // AIによる義務抽出
    const handleExtract = async (paymentSignature?: string) => {
        if (!contractId || isAnalyzing) return;

        // 外部からシグネチャが渡されていない場合、localStorageを確認
        const cacheKey = `payment_sig_${window.location.pathname}`;
        const cachedHash = localStorage.getItem(cacheKey);

        // 常に "tx_hash=0x..." の形式にする
        let effectiveSignature = paymentSignature;
        if (!effectiveSignature && cachedHash) {
            effectiveSignature = cachedHash.startsWith('tx_hash=') ? cachedHash : `tx_hash=${cachedHash}`;
        }

        setIsAnalyzing(true);
        setStatusMessage("AIが契約書を分析中...");
        try {
            const result = await api.extractObligations(contractId, undefined, effectiveSignature);

            const hasObligations = Array.isArray(result) && result.length > 0;

            if (!hasObligations) {
                alert("義務が抽出されませんでした。契約書の内容（PDFの文字が読み取れるか等）を確認するか、手動で登録してください。");
            }

            await loadObligations();

            // 支払い成功後の場合、モーダルを閉じる
            if (paymentSignature) {
                setShowPaymentModal(false);
                if (hasObligations) {
                    alert("支払いが確認され、AI分析が完了しました！");
                }
            }
            setStatusMessage(null);
        } catch (err: any) {
            // F8: x402 支払い要求の場合
            if (err.status === 402 && err.paymentInfo) {
                setPaymentInfo(err.paymentInfo);
                setShowPaymentModal(true);
                // 分析中は維持しない（モーダル操作待ち）
                setIsAnalyzing(false);
                setStatusMessage(null);
                return;
            }
            setError(err.message || '義務の抽出に失敗しました');
            setStatusMessage(null);
        } finally {
            if (!showPaymentModal) { // モーダル表示中はローディング解除しない（再試行のため）
                setIsAnalyzing(false);
            }
        }
    };

    // 支払い完了時のコールバック
    const handlePaymentComplete = async (txHash: string) => {
        // txHashは生ハッシュ (0x...) または prefix付きの場合があるが小文字化して統一
        const normalizedHash = txHash.toLowerCase();
        const signature = normalizedHash.startsWith('tx_hash=') ? normalizedHash : `tx_hash=${normalizedHash}`;

        console.log(`💎 Payment complete. Hash: ${normalizedHash}`);
        console.log(`🔑 Formatted signature: ${signature}`);

        // RPCの同期ラグを考慮して、少し長めに待機してから再試行する
        setIsAnalyzing(true);
        setStatusMessage("トランザクションを確認中... (5秒ほどお待ちください)");

        setTimeout(async () => {
            try {
                console.log("🔄 Retrying extraction with signature...");
                await handleExtract(signature);
                setStatusMessage(null);
            } catch (err: any) {
                console.error("❌ Post-payment extraction failed:", err);
                // 402が再度出た場合は、再度モーダルが出るので特に対処不要だが、
                // それ以外のエラーは表示する
                if (err.status !== 402) {
                    setError(err.message || '再試行に失敗しました');
                }
                setIsAnalyzing(false);
                setStatusMessage(null);
            }
        }, 5000); // 5秒待機
    };

    // 義務の完了
    const handleComplete = async (obligationId: string) => {
        if (!window.confirm('この義務を完了済みにしますか？')) return;

        // 開発用ダミーアドレス (実際はWalletContextから取得すべき)
        const dummyAddress = "0x1234567890123456789012345678901234567890";

        setIsProcessing(true);
        try {
            await api.completeObligation(obligationId, dummyAddress);
            await loadObligations();
        } catch (err: any) {
            alert(err.message || '更新に失敗しました');
        } finally {
            setIsProcessing(false);
        }
    };

    // 編集の保存
    const handleUpdate = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!editingObligation) return;

        // 開発用ダミーアドレス
        const dummyAddress = "0x1234567890123456789012345678901234567890";

        setIsProcessing(true);
        try {
            await api.updateObligation(editingObligation.id, {
                ...editingObligation,
                edited_by: dummyAddress
            });
            setEditingObligation(null);
            await loadObligations();
        } catch (err: any) {
            alert(err.message || '更新に失敗しました');
        } finally {
            setIsProcessing(false);
        }
    };

    // ステータスに応じたアイコンを返す
    const getStatusIcon = (status: ObligationStatus) => {
        switch (status) {
            case 'completed':
                return <CheckCircle size={20} className="status-icon completed" />;
            case 'overdue':
                return <XCircle size={20} className="status-icon overdue" />;
            case 'due_soon':
                return <AlertCircle size={20} className="status-icon due-soon" />;
            default:
                return <Clock size={20} className="status-icon pending" />;
        }
    };

    // ステータスの日本語表示
    const getStatusText = (status: ObligationStatus) => {
        const statusMap: Record<ObligationStatus, string> = {
            pending: '保留中',
            due_soon: '期限間近',
            completed: '完了',
            overdue: '期限超過',
            disputed: '係争中'
        };
        return statusMap[status];
    };

    // タイプの日本語表示
    const getTypeText = (type: ObligationType) => {
        const typeMap: Record<ObligationType, string> = {
            payment: '支払',
            renewal: '更新',
            termination: '解除',
            inspection: '検収',
            delivery: '納品',
            report: '報告',
            confidentiality: '秘密保持',
            other: 'その他'
        };
        return typeMap[type];
    };

    // リスクレベルの色クラス
    const getRiskClass = (risk: RiskLevel) => {
        return `risk-${risk}`;
    };

    // 日付のフォーマット
    const formatDate = (dateString: string | null) => {
        if (!dateString) return '未設定';
        const date = new Date(dateString);
        return date.toLocaleDateString('ja-JP', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit'
        });
    };

    // フィルタリングされた義務リスト
    const filteredObligations = obligations.filter(ob => {
        if (filter.type && ob.type !== filter.type) return false;
        if (filter.status && ob.status !== filter.status) return false;
        if (filter.risk && ob.risk_level !== filter.risk) return false;
        return true;
    });

    // ローディング中
    if (loading) {
        return (
            <div className="obligation-timeline">
                <div className="loading-state">
                    <div className="spinner"></div>
                    <p>義務を読み込み中...</p>
                </div>
            </div>
        );
    }

    // エラー表示
    if (error) {
        return (
            <div className="obligation-timeline">
                <div className="error-state">
                    <AlertCircle size={48} />
                    <h3>エラー</h3>
                    <p>{error}</p>
                    <button className="btn btn-primary" onClick={loadObligations}>
                        再読み込み
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="obligation-timeline">
            {/* ヘッダー */}
            <div className="timeline-header">
                <div className="header-title">
                    <Calendar size={32} />
                    <div>
                        <h1>義務カレンダー</h1>
                        <p>契約上の義務・期限を管理</p>
                    </div>
                </div>
                <Link to={`/contracts/${contractId}`} className="btn btn-secondary">
                    <FileText size={20} />
                    契約詳細へ戻る
                </Link>
            </div>

            {/* ステータスメッセージ表示 */}
            {statusMessage && (
                <div className="status-banner mb-6 p-4 bg-primary/10 text-primary rounded-lg flex items-center gap-3 shadow-sm border border-primary/20 animate-in fade-in slide-in-from-top-4 duration-300">
                    <Clock size={20} className="animate-spin" />
                    <span className="font-medium">{statusMessage}</span>
                </div>
            )}

            {/* フィルタ */}
            <div className="timeline-filters">
                <div className="filter-group">
                    <label>タイプ</label>
                    <select
                        value={filter.type || ''}
                        onChange={(e) => setFilter({ ...filter, type: e.target.value as ObligationType || undefined })}
                    >
                        <option value="">すべて</option>
                        <option value="payment">支払</option>
                        <option value="renewal">更新</option>
                        <option value="termination">解除</option>
                        <option value="inspection">検収</option>
                        <option value="delivery">納品</option>
                        <option value="report">報告</option>
                    </select>
                </div>

                <div className="filter-group">
                    <label>ステータス</label>
                    <select
                        value={filter.status || ''}
                        onChange={(e) => setFilter({ ...filter, status: e.target.value as ObligationStatus || undefined })}
                    >
                        <option value="">すべて</option>
                        <option value="pending">保留中</option>
                        <option value="due_soon">期限間近</option>
                        <option value="completed">完了</option>
                        <option value="overdue">期限超過</option>
                    </select>
                </div>

                <div className="filter-group">
                    <label>リスク</label>
                    <select
                        value={filter.risk || ''}
                        onChange={(e) => setFilter({ ...filter, risk: e.target.value as RiskLevel || undefined })}
                    >
                        <option value="">すべて</option>
                        <option value="high">高</option>
                        <option value="medium">中</option>
                        <option value="low">低</option>
                    </select>
                </div>
            </div>

            {/* 義務リスト */}
            {filteredObligations.length === 0 ? (
                <div className="empty-state">
                    <Calendar size={64} />
                    <h3>義務が見つかりません</h3>
                    <p>この契約にはまだ義務が登録されていません</p>
                    <button
                        className="btn btn-primary mt-4"
                        onClick={() => handleExtract()}
                        disabled={isAnalyzing}
                    >
                        {isAnalyzing ? (
                            <>
                                <span className="spinner-sm mr-2"></span>
                                {statusMessage || "AI分析中..."}
                            </>
                        ) : (
                            <>
                                <Play size={16} className="mr-2" />
                                AIで義務を抽出する
                            </>
                        )}
                    </button>
                    {isAnalyzing && statusMessage && (
                        <div className="status-banner mt-4 p-3 bg-info/10 text-info rounded-lg flex items-center gap-2">
                            <Clock size={16} className="animate-spin" />
                            <span>{statusMessage}</span>
                        </div>
                    )}
                </div>
            ) : (
                <div className="obligations-list">
                    {filteredObligations.map((obligation) => (
                        <div key={obligation.id} className={`obligation-card ${getRiskClass(obligation.risk_level)}`}>
                            {/* ステータスバッジ */}
                            <div className="obligation-status">
                                {getStatusIcon(obligation.status)}
                                <span>{getStatusText(obligation.status)}</span>
                            </div>

                            {/* 義務情報 */}
                            <div className="obligation-info">
                                <div className="obligation-header">
                                    <h3>{obligation.title}</h3>
                                    <span className={`type-badge ${obligation.type}`}>
                                        {getTypeText(obligation.type)}
                                    </span>
                                </div>

                                <div className="obligation-details">
                                    <div className="detail-row">
                                        <strong>実行内容:</strong>
                                        <span>{obligation.action}</span>
                                    </div>

                                    {obligation.due_date && (
                                        <div className="detail-row">
                                            <strong>期限:</strong>
                                            <span className="due-date">{formatDate(obligation.due_date)}</span>
                                        </div>
                                    )}

                                    {obligation.trigger_condition && (
                                        <div className="detail-row">
                                            <strong>条件:</strong>
                                            <span>{obligation.trigger_condition}</span>
                                        </div>
                                    )}

                                    {obligation.clause_reference && (
                                        <div className="detail-row clause-reference">
                                            <strong>根拠条項:</strong>
                                            <span>{obligation.clause_reference}</span>
                                        </div>
                                    )}

                                    {obligation.notes && (
                                        <div className="detail-row notes">
                                            <strong>備考:</strong>
                                            <span>{obligation.notes}</span>
                                        </div>
                                    )}
                                </div>

                                {/* 必要な証跡 */}
                                {obligation.evidence_required && obligation.evidence_required.length > 0 && (
                                    <div className="evidence-required">
                                        <strong>必要な証跡:</strong>
                                        <ul>
                                            {obligation.evidence_required.map((evidence, index) => (
                                                <li key={index}>{evidence}</li>
                                            ))}
                                        </ul>
                                    </div>
                                )}
                            </div>

                            {/* リスクインジケーター */}
                            <div className={`risk-indicator ${getRiskClass(obligation.risk_level)}`}>
                                リスク: {obligation.risk_level === 'high' ? '高' : obligation.risk_level === 'medium' ? '中' : '低'}
                            </div>
                            <div className="obligation-actions">
                                <button
                                    className="btn btn-ghost btn-sm"
                                    onClick={() => setEditingObligation(obligation)}
                                >
                                    <Edit2 size={16} /> 編集
                                </button>
                                {obligation.status !== 'completed' && (
                                    <button
                                        className="btn btn-success-outline btn-sm"
                                        onClick={() => handleComplete(obligation.id)}
                                        disabled={isProcessing}
                                    >
                                        <Check size={16} /> 完了にする
                                    </button>
                                )}
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {/* 編集モーダル */}
            {editingObligation && (
                <div className="modal-overlay" onClick={() => setEditingObligation(null)}>
                    <div className="modal-content card" onClick={e => e.stopPropagation()}>
                        <h3>義務を編集</h3>
                        <form onSubmit={handleUpdate}>
                            <div className="form-group">
                                <label className="form-label">タイトル</label>
                                <input
                                    type="text"
                                    className="input"
                                    value={editingObligation.title}
                                    onChange={e => setEditingObligation({ ...editingObligation, title: e.target.value })}
                                    required
                                />
                            </div>
                            <div className="form-group">
                                <label className="form-label">期限</label>
                                <input
                                    type="date"
                                    className="input"
                                    value={editingObligation.due_date ? new Date(editingObligation.due_date).toISOString().split('T')[0] : ''}
                                    onChange={e => setEditingObligation({ ...editingObligation, due_date: e.target.value ? new Date(e.target.value).toISOString() : null })}
                                />
                            </div>
                            <div className="form-group">
                                <label className="form-label">ステータス</label>
                                <select
                                    className="input"
                                    value={editingObligation.status}
                                    onChange={e => setEditingObligation({ ...editingObligation, status: e.target.value as ObligationStatus })}
                                >
                                    <option value="pending">保留中</option>
                                    <option value="due_soon">期限間近</option>
                                    <option value="completed">完了</option>
                                    <option value="overdue">期限超過</option>
                                </select>
                            </div>
                            <div className="modal-actions mt-6">
                                <button type="submit" className="btn btn-primary" disabled={isProcessing}>保存</button>
                                <button type="button" className="btn btn-ghost" onClick={() => setEditingObligation(null)}>キャンセル</button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
            {/* 支払いモーダル */}
            {paymentInfo && (
                <PaymentModal
                    isOpen={showPaymentModal}
                    onClose={() => { setShowPaymentModal(false); setIsAnalyzing(false); }}
                    paymentInfo={paymentInfo}
                    onPaymentComplete={handlePaymentComplete}
                />
            )}
        </div>
    );
};

export default ObligationTimeline;
