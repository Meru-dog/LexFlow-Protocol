/**
 * LexFlow Protocol - コントラクト詳細ページ
 */
import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
    FileText,
    AlertCircle,
    ArrowLeft,
    Shield,
    Plus,
    Gavel,
    ExternalLink,
    Calendar,
    History as HistoryIcon
} from 'lucide-react';
import { api, getFileUrl } from '../services/api';
import { useWallet } from '../contexts/WalletContext';
import type { ContractWithDetails, Condition } from '../types';
import './ContractDetail.css';

export function ContractDetail() {
    const { id } = useParams<{ id: string }>();
    const navigate = useNavigate();
    const { isConnected, address } = useWallet();

    const [contract, setContract] = useState<ContractWithDetails | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [activating, setActivating] = useState(false);

    // モーダル状態
    const [showAddCondition, setShowAddCondition] = useState(false);
    const [showEvidenceModal, setShowEvidenceModal] = useState<string | null>(null);
    const [showApproveModal, setShowApproveModal] = useState<string | null>(null);
    const [aiJudgment, setAiJudgment] = useState<any>(null);
    const [loadingAi, setLoadingAi] = useState(false);
    const [contractText, setContractText] = useState<string>('');
    const [loadingText, setLoadingText] = useState(false);

    // AI理由からJSONを抽出してパースする関数
    const parseAiReason = (reason: string): string => {
        if (!reason) return '理由が提供されていません';

        // JSONが含まれている場合は抽出
        const jsonMatch = reason.match(/```json\s*({[\s\S]*?})\s*```/);
        if (jsonMatch) {
            try {
                const parsed = JSON.parse(jsonMatch[1]);
                return parsed.reason || reason;
            } catch (e) {
                // JSON解析失敗時は元の文字列を返す
            }
        }

        // 「AI応答の解析に失敗しました」で始まる場合、実際のJSONを抽出
        if (reason.includes('AI応答の解析に失敗しました')) {
            try {
                const jsonStart = reason.indexOf('{');
                if (jsonStart !== -1) {
                    const jsonStr = reason.substring(jsonStart);
                    const parsed = JSON.parse(jsonStr);
                    return parsed.reason || '判定理由を取得できませんでした';
                }
            } catch (e) {
                return '判定理由の解析に失敗しました';
            }
        }

        return reason;
    };

    // モーダルを開くとき
    const openApproveModal = async (conditionId: string) => {
        setShowApproveModal(conditionId);
        setLoadingAi(true);
        try {
            const result = await api.getJudgment(conditionId);
            setAiJudgment(result);
        } catch (err) {
            console.log('AI判断データが見つかりませんでした - これは条件の証拠が提出されていない場合の正常な動作です');
            setAiJudgment(null);
        } finally {
            setLoadingAi(false);
        }
    };

    // フォーム状態
    const [newCondition, setNewCondition] = useState({
        condition_type: 'milestone',
        description: '',
        payment_amount: 0,
        recipient_address: ''
    });
    const [evidence, setEvidence] = useState({
        evidence_text: '',
        evidence_url: ''
    });
    const [approval, setApproval] = useState<{ result: 'approved' | 'rejected', comment: string }>({
        result: 'approved',
        comment: ''
    });

    // データの取得
    useEffect(() => {
        if (id) {
            loadContract();
        }
    }, [id]);

    const loadContract = async () => {
        try {
            setLoading(true);
            const data = await api.getContract(id!);
            setContract(data as ContractWithDetails);

            // 契約書テキストの読み込み
            loadContractText(id!);
        } catch (err: any) {
            setError(err.message || '契約詳細の読み込みに失敗しました');
        } finally {
            setLoading(false);
        }
    };

    const loadContractText = async (contractId: string) => {
        try {
            setLoadingText(true);
            const res = await api.getContractText(contractId);
            setContractText(res.text);
        } catch (err) {
            console.error('Failed to load contract text:', err);
        } finally {
            setLoadingText(false);
        }
    };

    // コントラクトのアクティベート
    const handleActivate = async () => {
        if (!id) return;
        setActivating(true);
        try {
            await api.activateContract(id);
            await loadContract();
        } catch (err: any) {
            alert(err.message || '契約の有効化に失敗しました');
        } finally {
            setActivating(false);
        }
    };

    // 条件の追加
    const handleAddCondition = async () => {
        if (!id) return;

        // バリデーション
        if (newCondition.payment_amount <= 0) {
            alert('金額は0より大きい値を入力してください');
            return;
        }

        const addressRegex = /^0x[a-fA-F0-9]{40}$/;
        if (!addressRegex.test(newCondition.recipient_address)) {
            alert('有効なEthereumアドレスを入力してください (0x...)');
            return;
        }

        try {
            await api.addCondition(id, newCondition);
            setShowAddCondition(false);
            setNewCondition({
                condition_type: 'milestone',
                description: '',
                payment_amount: 0,
                recipient_address: ''
            });
            await loadContract();
        } catch (err: any) {
            alert(err.message || '条件の追加に失敗しました');
        }
    };

    // 証拠の提出
    const handleSubmitEvidence = async (conditionId: string) => {
        try {
            await api.submitEvidence(conditionId, evidence);
            setShowEvidenceModal(null);
            setEvidence({ evidence_text: '', evidence_url: '' });
            await loadContract();
        } catch (err: any) {
            alert(err.message || '証拠の提出に失敗しました');
        }
    };

    // 承認
    const handleApprove = async (conditionId: string) => {
        try {
            await api.approveCondition(conditionId, approval, address || undefined);
            setShowApproveModal(null);
            setApproval({ result: 'approved', comment: '' });
            await loadContract();
        } catch (err: any) {
            alert(err.message || '条件の承認/却下に失敗しました');
        }
    };

    // 金額のフォーマット
    const formatCurrency = (value: number) => {
        return new Intl.NumberFormat('ja-JP', {
            style: 'currency',
            currency: 'JPY',
            maximumFractionDigits: 0,
        }).format(value);
    };

    if (loading) {
        return (
            <div className="contract-detail">
                <div className="loading-state">
                    <div className="spinner"></div>
                    <p>契約詳細を読み込み中...</p>
                </div>
            </div>
        );
    }

    if (error || !contract) {
        return (
            <div className="contract-detail">
                <div className="error-message card">
                    <AlertCircle size={48} />
                    <h3>エラー</h3>
                    <p>{error || '契約が見つかりませんでした'}</p>
                    <button className="btn btn-primary" onClick={() => navigate('/contracts')}>
                        契約一覧に戻る
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="contract-detail">
            {/* Header */}
            <div className="detail-header">
                <div className="detail-header-info">
                    <button className="btn btn-ghost btn-sm mb-4" onClick={() => navigate('/contracts')}>
                        <ArrowLeft size={16} /> 契約一覧に戻る
                    </button>
                    <h1>{contract.title}</h1>
                    <div className="detail-header-meta">
                        <span className="badge badge-neutral">ID: {contract.id}</span>
                        <span>作成日: {new Date(contract.created_at).toLocaleDateString('ja-JP')}</span>
                    </div>
                </div>
                <div className="detail-header-actions">
                    <button
                        className="btn btn-secondary mr-2"
                        onClick={() => navigate(`/contracts/${id}/obligations`)}
                    >
                        <Calendar size={16} className="mr-2" />
                        義務カレンダー
                    </button>
                    <button
                        className="btn btn-secondary mr-2"
                        onClick={() => navigate(`/contracts/${id}/versions`)}
                    >
                        <HistoryIcon size={16} className="mr-2" />
                        署名・版管理
                    </button>
                    {contract.status === 'pending' && (
                        <button
                            className="btn btn-primary"
                            onClick={handleActivate}
                            disabled={activating || !isConnected}
                        >
                            {activating ? '有効化中...' : '契約を有効化'}
                        </button>
                    )}
                    {contract.status === 'active' && (
                        <span className="badge badge-success-lg">
                            <Shield size={20} /> Active
                        </span>
                    )}
                </div>
            </div>

            <div className="detail-grid">
                {/* Main Content */}
                <div className="main-content">
                    {/* Summary Card */}
                    <div className="detail-section card">
                        <h2><FileText size={20} /> 要約</h2>
                        <p className="text-secondary">{contract.parsed_data?.summary || '要約がありません。'}</p>
                    </div>

                    {/* Conditions Section */}
                    <div className="detail-section">
                        <div className="section-header">
                            <h2><Gavel size={20} /> 支払条件</h2>
                            {contract.status === 'pending' && (
                                <button className="btn btn-secondary btn-sm" onClick={() => setShowAddCondition(true)}>
                                    <Plus size={16} /> 条件を追加
                                </button>
                            )}
                        </div>

                        <div className="conditions-list">
                            {contract.conditions?.length === 0 ? (
                                <div className="empty-state-small card">
                                    <p>まだ支払条件が追加されていません。</p>
                                </div>
                            ) : (
                                contract.conditions?.map((cond: Condition) => (
                                    <div key={cond.id} className="condition-item card">
                                        <div className="condition-header">
                                            <span className="condition-type">{cond.condition_type}</span>
                                            <span className={`badge badge-${cond.status === 'executed' ? 'success' :
                                                cond.status === 'rejected' ? 'error' :
                                                    cond.status === 'judging' ? 'info' : 'warning'
                                                }`}>
                                                {cond.status}
                                            </span>
                                        </div>
                                        <p className="condition-desc">{cond.description}</p>
                                        <div className="condition-footer">
                                            <div className="condition-amount">
                                                {formatCurrency(cond.payment_amount)}
                                            </div>
                                            <div className="condition-actions">
                                                {cond.status === 'pending' && contract.status === 'active' && (
                                                    <button className="btn btn-secondary btn-sm" onClick={() => setShowEvidenceModal(cond.id)}>
                                                        証拠を提出
                                                    </button>
                                                )}
                                                {cond.status === 'judging' && (
                                                    <button className="btn btn-primary btn-sm" onClick={() => openApproveModal(cond.id)}>
                                                        判定する
                                                    </button>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                ))
                            )}
                        </div>
                    </div>

                    {/* Blockchain Activity Timeline */}
                    {contract.blockchain_tx_hash && (
                        <div className="detail-section">
                            <h2>⛓️ ブロックチェーン活動</h2>
                            <div className="timeline">
                                {/* Contract Created Event */}
                                <div className="timeline-item">
                                    <div className="timeline-marker success"></div>
                                    <div className="timeline-content card">
                                        <div className="timeline-header">
                                            <h4>📝 契約作成</h4>
                                            <span className="timeline-date">{new Date(contract.created_at).toLocaleString('ja-JP')}</span>
                                        </div>
                                        <div className="timeline-details">
                                            <div className="detail-row">
                                                <span>契約ID:</span>
                                                <code className="code-block">{contract.id}</code>
                                            </div>
                                            <div className="detail-row">
                                                <span>総額:</span>
                                                <strong>{formatCurrency(contract.total_amount)}</strong>
                                            </div>
                                            <div className="detail-row">
                                                <span>弁護士:</span>
                                                <code className="code-inline">{contract.lawyer_address}</code>
                                            </div>
                                            <a
                                                href={`https://sepolia.etherscan.io/tx/${contract.blockchain_tx_hash.startsWith('0x') ? contract.blockchain_tx_hash : '0x' + contract.blockchain_tx_hash}#eventlog`}
                                                target="_blank"
                                                rel="noreferrer"
                                                className="btn btn-ghost btn-sm mt-2"
                                            >
                                                Etherscanでイベントを見る →
                                            </a>
                                        </div>
                                    </div>
                                </div>

                                {/* Conditions Events */}
                                {contract.conditions?.map((cond: Condition) => (
                                    <div key={cond.id} className="timeline-item">
                                        <div className={`timeline-marker ${cond.status === 'executed' ? 'success' :
                                            cond.status === 'approved' ? 'info' :
                                                cond.status === 'judging' ? 'warning' : 'default'
                                            }`}></div>
                                        <div className="timeline-content card">
                                            <div className="timeline-header">
                                                <h4>
                                                    {cond.status === 'executed' && '✅ 支払実行済み'}
                                                    {cond.status === 'approved' && '👍 条件承認済み'}
                                                    {cond.status === 'judging' && '📋 証拠提出済み'}
                                                    {cond.status === 'pending' && '⏳ 条件追加済み'}
                                                </h4>
                                                <span className="timeline-date">{new Date(cond.created_at).toLocaleString('ja-JP')}</span>
                                            </div>
                                            <div className="timeline-details">
                                                <div className="detail-row">
                                                    <span>条件:</span>
                                                    <span>{cond.description}</span>
                                                </div>
                                                <div className="detail-row">
                                                    <span>金額:</span>
                                                    <strong>{formatCurrency(cond.payment_amount)}</strong>
                                                </div>
                                                <div className="detail-row">
                                                    <span>受取人:</span>
                                                    <code className="code-inline">{cond.recipient_address}</code>
                                                </div>
                                                {cond.status === 'executed' && cond.executed_at && (
                                                    <div className="detail-row">
                                                        <span>実行日時:</span>
                                                        <span>{new Date(cond.executed_at).toLocaleString('ja-JP')}</span>
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </div>

                {/* Sidebar */}
                <div className="sidebar">
                    {/* Status Overview Card */}
                    <div className="sidebar-card card">
                        <h3>📊 契約ステータス</h3>
                        <div className="status-overview">
                            <div className={`status-badge-large ${contract.status}`}>
                                {contract.status === 'pending' && '⏳ 有効化待ち'}
                                {contract.status === 'active' && '✅ 有効'}
                                {contract.status === 'completed' && '🎉 完了'}
                            </div>

                            {/* Progress Bar */}
                            <div className="progress-section">
                                <div className="progress-label">
                                    <span>支払進捗</span>
                                    <span className="progress-percentage">
                                        {contract.total_amount > 0
                                            ? Math.round((contract.released_amount / contract.total_amount) * 100)
                                            : 0}%
                                    </span>
                                </div>
                                <div className="progress-bar">
                                    <div
                                        className="progress-fill"
                                        style={{
                                            width: `${contract.total_amount > 0
                                                ? (contract.released_amount / contract.total_amount) * 100
                                                : 0}%`
                                        }}
                                    />
                                </div>
                                <div className="progress-amounts">
                                    <span>{formatCurrency(contract.released_amount)} 発行済み</span>
                                    <span>{formatCurrency(contract.total_amount)} 総額</span>
                                </div>
                            </div>

                            {/* Conditions Summary */}
                            <div className="conditions-summary">
                                <h4>条件概要</h4>
                                <div className="condition-stats">
                                    <div className="stat-item">
                                        <span className="stat-number">{contract.conditions?.filter(c => c.status === 'executed').length || 0}</span>
                                        <span className="stat-label">実行済み</span>
                                    </div>
                                    <div className="stat-item">
                                        <span className="stat-number">{contract.conditions?.filter(c => c.status === 'judging').length || 0}</span>
                                        <span className="stat-label">判定中</span>
                                    </div>
                                    <div className="stat-item">
                                        <span className="stat-number">{contract.conditions?.filter(c => c.status === 'pending').length || 0}</span>
                                        <span className="stat-label">保留中</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Contract Details Card */}
                    <div className="sidebar-card card">
                        <h3>💼 契約詳細</h3>
                        <div className="info-row">
                            <span className="info-label">総額</span>
                            <span className="info-value highlight">{formatCurrency(contract.total_amount)}</span>
                        </div>
                        <div className="info-row">
                            <span className="info-label">発行済み</span>
                            <span className="info-value">{formatCurrency(contract.released_amount)}</span>
                        </div>
                        <div className="info-row">
                            <span className="info-label">残高</span>
                            <span className="info-value">{formatCurrency(contract.total_amount - contract.released_amount)}</span>
                        </div>
                        <div className="info-row">
                            <span className="info-label">支払者</span>
                            <span className="info-value font-mono truncate" title={contract.payer_address}>
                                {contract.payer_address?.slice(0, 6)}...{contract.payer_address?.slice(-4)}
                            </span>
                        </div>
                        <div className="info-row">
                            <span className="info-label">弁護士</span>
                            <span className="info-value font-mono truncate" title={contract.lawyer_address}>
                                {contract.lawyer_address?.slice(0, 6)}...{contract.lawyer_address?.slice(-4)}
                            </span>
                        </div>
                    </div>

                    {/* Blockchain Info Card */}
                    <div className="sidebar-card card">
                        <h3>⛓️ ブロックチェーン情報</h3>
                        <div className="info-row">
                            <span className="info-label">ネットワーク</span>
                            <span className="info-value">Sepolia テストネット</span>
                        </div>
                        <div className="info-row">
                            <span className="info-label">ステータス</span>
                            <span className={`badge badge-${contract.status === 'active' ? 'success' : 'warning'}`}>
                                {contract.status}
                            </span>
                        </div>
                        {contract.blockchain_tx_hash && (
                            <>
                                <div className="info-row">
                                    <span className="info-label">トランザクション</span>
                                    <a
                                        href={`https://sepolia.etherscan.io/tx/${contract.blockchain_tx_hash.startsWith('0x') ? contract.blockchain_tx_hash : '0x' + contract.blockchain_tx_hash}`}
                                        target="_blank"
                                        rel="noreferrer"
                                        className="info-value link"
                                    >
                                        表示 <ExternalLink size={12} />
                                    </a>
                                </div>
                                <div className="blockchain-actions">
                                    <a
                                        href={`https://sepolia.etherscan.io/tx/${contract.blockchain_tx_hash.startsWith('0x') ? contract.blockchain_tx_hash : '0x' + contract.blockchain_tx_hash}#eventlog`}
                                        target="_blank"
                                        rel="noreferrer"
                                        className="btn btn-secondary btn-sm w-full"
                                    >
                                        📜 ログを見る
                                    </a>
                                    <a
                                        href={`https://sepolia.etherscan.io/address/${contract.payer_address}`}
                                        target="_blank"
                                        rel="noreferrer"
                                        className="btn btn-ghost btn-sm w-full"
                                    >
                                        🔍 契約を見る
                                    </a>
                                </div>
                            </>
                        )}
                        <div className="info-row">
                            <span className="info-label">元のファイル</span>
                            <button className="btn btn-ghost btn-sm p-0 h-auto" onClick={() => window.open(getFileUrl(contract.file_url))}>
                                ダウンロード <ExternalLink size={12} />
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            {/* Modals */}
            {showAddCondition && (
                <div className="modal-overlay" onClick={() => setShowAddCondition(false)}>
                    <div className="modal-content card" onClick={e => e.stopPropagation()}>
                        <h3>支払条件を追加</h3>
                        <div className="form-group mt-4">
                            <label className="form-label">タイプ</label>
                            <select
                                className="input"
                                value={newCondition.condition_type}
                                onChange={e => setNewCondition({ ...newCondition, condition_type: e.target.value })}
                            >
                                <option value="milestone">マイルストーン</option>
                                <option value="deadline">期限</option>
                                <option value="approval">承認</option>
                            </select>
                        </div>
                        <div className="form-group">
                            <label className="form-label">説明</label>
                            <textarea
                                className="input"
                                rows={3}
                                placeholder="条件を説明してください..."
                                value={newCondition.description}
                                onChange={e => setNewCondition({ ...newCondition, description: e.target.value })}
                            />
                        </div>
                        <div className="form-group">
                            <label className="form-label">金額 (JPYC)</label>
                            <input
                                type="number"
                                className="input"
                                value={newCondition.payment_amount}
                                onChange={e => setNewCondition({ ...newCondition, payment_amount: Number(e.target.value) })}
                            />
                        </div>
                        <div className="form-group">
                            <label className="form-label">受取人アドレス</label>
                            <input
                                type="text"
                                className="input font-mono"
                                placeholder="0x..."
                                value={newCondition.recipient_address}
                                onChange={e => setNewCondition({ ...newCondition, recipient_address: e.target.value })}
                            />
                        </div>
                        <div className="modal-actions mt-6">
                            <button className="btn btn-primary" onClick={handleAddCondition}>条件を追加</button>
                            <button className="btn btn-ghost" onClick={() => setShowAddCondition(false)}>キャンセル</button>
                        </div>
                    </div>
                </div>
            )}

            {showEvidenceModal && (
                <div className="modal-overlay" onClick={() => setShowEvidenceModal(null)}>
                    <div className="modal-content card" onClick={e => e.stopPropagation()}>
                        <h3>証拠を提出</h3>
                        <p className="text-secondary mb-4">この条件が満たされたことを証明する資料を提供してください。AIが評価します。</p>
                        <div className="form-group">
                            <label className="form-label">証拠テキスト / 説明</label>
                            <textarea
                                className="input"
                                rows={4}
                                placeholder="証明内容を説明してください..."
                                value={evidence.evidence_text}
                                onChange={e => setEvidence({ ...evidence, evidence_text: e.target.value })}
                            />
                        </div>
                        <div className="form-group">
                            <label className="form-label">証拠URL（任意）</label>
                            <input
                                type="text"
                                className="input"
                                placeholder="https://..."
                                value={evidence.evidence_url}
                                onChange={e => setEvidence({ ...evidence, evidence_url: e.target.value })}
                            />
                        </div>
                        <div className="modal-actions mt-6">
                            <button className="btn btn-primary" onClick={() => handleSubmitEvidence(showEvidenceModal)}>レビューに提出</button>
                            <button className="btn btn-ghost" onClick={() => setShowEvidenceModal(null)}>キャンセル</button>
                        </div>
                    </div>
                </div>
            )}

            {showApproveModal && (
                <div className="modal-overlay" onClick={() => setShowApproveModal(null)}>
                    <div className="modal-content card" onClick={e => e.stopPropagation()}>
                        <h3>条件を判定</h3>
                        <p className="text-secondary mb-4">AI評価を確認し、最終決定を行ってください。承認された条件はJPYC支払いを実行します。</p>

                        {loadingAi ? (
                            <div className="flex items-center gap-2 mb-4 p-3 bg-neutral rounded">
                                <div className="spinner-sm"></div>
                                <span>AI評価を読み込み中...</span>
                            </div>
                        ) : aiJudgment ? (
                            <div className="ai-assessment-card">
                                <div className="assessment-header">
                                    <div className={`assessment-result ${aiJudgment.ai_result?.toLowerCase()}`}>
                                        <Shield size={20} />
                                        <span className="result-label">
                                            {aiJudgment.ai_result?.toUpperCase() === 'APPROVED' && '✓ 承認推奨'}
                                            {aiJudgment.ai_result?.toUpperCase() === 'REJECTED' && '✗ 却下推奨'}
                                            {aiJudgment.ai_result?.toUpperCase() === 'NEEDS_REVIEW' && '⚠ 要確認'}
                                        </span>
                                    </div>
                                    <div className="confidence-score">
                                        <span className="confidence-label">信頼度</span>
                                        <span className="confidence-value">{(aiJudgment.ai_confidence * 100).toFixed(0)}%</span>
                                    </div>
                                </div>
                                <div className="assessment-reason">
                                    <h4 className="reason-title">判定理由</h4>
                                    <p className="reason-text">{parseAiReason(aiJudgment.ai_reason)}</p>
                                </div>
                            </div>
                        ) : (
                            <div className="mb-4 p-4 bg-neutral rounded">
                                <p className="text-sm opacity-70">AI評価データがありません。</p>
                            </div>
                        )}

                        <div className="form-group">
                            <label className="form-label">決定</label>
                            <div className="flex gap-4">
                                <label className="flex items-center gap-2 cursor-pointer">
                                    <input
                                        type="radio"
                                        name="decision"
                                        checked={approval.result === 'approved'}
                                        onChange={() => setApproval({ ...approval, result: 'approved' })}
                                    />
                                    承認して支払う
                                </label>
                                <label className="flex items-center gap-2 cursor-pointer">
                                    <input
                                        type="radio"
                                        name="decision"
                                        checked={approval.result === 'rejected'}
                                        onChange={() => setApproval({ ...approval, result: 'rejected' })}
                                    />
                                    却下
                                </label>
                            </div>
                        </div>

                        <div className="form-group">
                            <label className="form-label">コメント</label>
                            <textarea
                                className="input"
                                rows={3}
                                placeholder="コメントを追加..."
                                value={approval.comment}
                                onChange={e => setApproval({ ...approval, comment: e.target.value })}
                            />
                        </div>

                        <div className="modal-actions mt-6">
                            <button className="btn btn-primary" onClick={() => handleApprove(showApproveModal)}>決定を確定</button>
                            <button className="btn btn-ghost" onClick={() => setShowApproveModal(null)}>キャンセル</button>
                        </div>
                    </div>
                </div>
            )}

            {/* Contract Full Text Section */}
            <div className="detail-section card mt-8">
                <div className="flex justify-between items-center mb-4">
                    <h2><FileText size={20} /> 契約書全文</h2>
                    {contract.file_url && (
                        <a
                            href={getFileUrl(contract.file_url)}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-sm text-primary hover:text-primary-focus bg-neutral px-3 py-1 rounded-full flex items-center gap-1 transition-colors font-medium"
                        >
                            ファイルを表示 <ExternalLink size={12} />
                        </a>
                    )}
                </div>
                {loadingText ? (
                    <div className="flex items-center gap-2 p-4">
                        <div className="spinner-sm"></div>
                        <span>テキストを抽出中...</span>
                    </div>
                ) : contractText ? (
                    <div className="contract-full-text">
                        {contractText}
                    </div>
                ) : (
                    <p className="text-secondary p-4">テキストを読み込めませんでした。</p>
                )}
            </div>
        </div>
    );
}
