import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { GitCompareArrows, ArrowLeft, AlertTriangle, CheckCircle, Info, RefreshCw, FileText } from 'lucide-react';
import { api } from '../services/api';
import './RedlineCompare.css';

interface Version {
    id: string;
    version: number;
    title: string;
    created_at: string;
}

interface ChangeItem {
    change_type: string;
    location: string;
    old_text: string | null;
    new_text: string | null;
    risk_level: string;
    risk_reason: string | null;
    recommendation: string | null;
}

interface RiskAssessment {
    high_risk_count: number;
    medium_risk_count: number;
    low_risk_count: number;
    overall_risk: string;
    summary: string;
}

interface RedlineResult {
    old_version_id: string;
    new_version_id: string;
    changes: ChangeItem[];
    summary: string;
    risk_assessment: RiskAssessment;
    recommendations: string[];
    diff_html: string;
}

const RedlineCompare: React.FC = () => {
    const { contractId } = useParams<{ contractId: string }>();
    const [versions, setVersions] = useState<Version[]>([]);
    const [oldVersionId, setOldVersionId] = useState<string>('');
    const [newVersionId, setNewVersionId] = useState<string>('');
    const [result, setResult] = useState<RedlineResult | null>(null);
    const [loading, setLoading] = useState(false);
    const [versionsLoading, setVersionsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (contractId) {
            loadVersions();
        }
    }, [contractId]);

    const loadVersions = async () => {
        try {
            setVersionsLoading(true);
            const data = await api.getVersionsByCase(contractId!);
            setVersions(data as Version[]);
            // デフォルト選択: 最新2つのバージョン
            if ((data as Version[]).length >= 2) {
                setOldVersionId((data as Version[])[1].id);
                setNewVersionId((data as Version[])[0].id);
            }
        } catch (err: any) {
            setError(err.message || "Failed to load versions");
        } finally {
            setVersionsLoading(false);
        }
    };

    const handleCompare = async () => {
        if (!oldVersionId || !newVersionId) {
            setError("比較するバージョンを選択してください");
            return;
        }
        if (oldVersionId === newVersionId) {
            setError("異なるバージョンを選択してください");
            return;
        }

        setLoading(true);
        setError(null);
        setResult(null);

        try {
            const data = await api.compareVersions(oldVersionId, newVersionId);
            setResult(data as RedlineResult);
        } catch (err: any) {
            setError(err.message || "比較に失敗しました");
        } finally {
            setLoading(false);
        }
    };

    const getRiskBadgeClass = (level: string) => {
        switch (level) {
            case 'high': return 'risk-badge high';
            case 'medium': return 'risk-badge medium';
            case 'low': return 'risk-badge low';
            default: return 'risk-badge';
        }
    };

    const getRiskIcon = (level: string) => {
        switch (level) {
            case 'high': return <AlertTriangle size={16} />;
            case 'medium': return <Info size={16} />;
            case 'low': return <CheckCircle size={16} />;
            default: return null;
        }
    };

    const formatDate = (dateString: string) => {
        return new Date(dateString).toLocaleString('ja-JP');
    };

    if (versionsLoading) {
        return <div className="loading">バージョン情報を読み込み中...</div>;
    }

    return (
        <div className="redline-page">
            <header className="page-header">
                <Link to={`/contracts/${contractId}/versions`} className="back-link">
                    <ArrowLeft size={18} /> 版管理へ戻る
                </Link>
                <div className="header-main">
                    <div className="title-group">
                        <GitCompareArrows size={32} />
                        <div>
                            <h1>Redline 比較</h1>
                            <p>AIによる契約書変更点の解析とリスク評価</p>
                        </div>
                    </div>
                </div>
            </header>

            {/* バージョン選択セクション */}
            <section className="version-selector card">
                <h2>比較するバージョンを選択</h2>
                <div className="selector-row">
                    <div className="selector-item">
                        <label>旧バージョン</label>
                        <select
                            value={oldVersionId}
                            onChange={(e) => setOldVersionId(e.target.value)}
                            disabled={loading}
                        >
                            <option value="">選択してください</option>
                            {versions.map(v => (
                                <option key={v.id} value={v.id}>
                                    Ver.{v.version} - {v.title} ({formatDate(v.created_at)})
                                </option>
                            ))}
                        </select>
                    </div>
                    <div className="selector-arrow">⇄</div>
                    <div className="selector-item">
                        <label>新バージョン</label>
                        <select
                            value={newVersionId}
                            onChange={(e) => setNewVersionId(e.target.value)}
                            disabled={loading}
                        >
                            <option value="">選択してください</option>
                            {versions.map(v => (
                                <option key={v.id} value={v.id}>
                                    Ver.{v.version} - {v.title} ({formatDate(v.created_at)})
                                </option>
                            ))}
                        </select>
                    </div>
                    <button
                        className="btn btn-primary compare-btn"
                        onClick={handleCompare}
                        disabled={loading || !oldVersionId || !newVersionId}
                    >
                        {loading ? (
                            <>
                                <RefreshCw size={18} className="spin" />
                                解析中...
                            </>
                        ) : (
                            <>
                                <GitCompareArrows size={18} />
                                比較実行
                            </>
                        )}
                    </button>
                </div>
                {versions.length < 2 && (
                    <div className="warning-message">
                        <AlertTriangle size={16} />
                        比較には2つ以上のバージョンが必要です。新しいバージョンをアップロードしてください。
                    </div>
                )}
            </section>

            {error && (
                <div className="error-message card">
                    <AlertTriangle size={20} />
                    {error}
                </div>
            )}

            {/* 結果表示 */}
            {result && (
                <div className="results-section">
                    {/* リスク評価サマリー */}
                    <section className="risk-summary card">
                        <h2>AIリスク評価</h2>
                        <div className="risk-overview">
                            <div className={`overall-risk ${result.risk_assessment.overall_risk}`}>
                                {getRiskIcon(result.risk_assessment.overall_risk)}
                                <span>総合リスク: {result.risk_assessment.overall_risk === 'high' ? '高' : result.risk_assessment.overall_risk === 'medium' ? '中' : '低'}</span>
                            </div>
                            <div className="risk-counts">
                                <div className="risk-count high">
                                    <AlertTriangle size={16} />
                                    高リスク: {result.risk_assessment.high_risk_count}件
                                </div>
                                <div className="risk-count medium">
                                    <Info size={16} />
                                    中リスク: {result.risk_assessment.medium_risk_count}件
                                </div>
                                <div className="risk-count low">
                                    <CheckCircle size={16} />
                                    低リスク: {result.risk_assessment.low_risk_count}件
                                </div>
                            </div>
                        </div>
                        <p className="risk-summary-text">{result.risk_assessment.summary}</p>
                    </section>

                    {/* AI要約 */}
                    <section className="summary-section card">
                        <h2>変更内容の要約</h2>
                        <p>{result.summary}</p>
                    </section>

                    {/* 変更詳細 */}
                    <section className="changes-section card">
                        <h2>変更詳細</h2>
                        {result.changes.length === 0 ? (
                            <p className="no-changes">変更点が検出されませんでした。</p>
                        ) : (
                            <div className="changes-list">
                                {result.changes.map((change, index) => (
                                    <div key={index} className={`change-item ${change.risk_level}`}>
                                        <div className="change-header">
                                            <span className={getRiskBadgeClass(change.risk_level)}>
                                                {getRiskIcon(change.risk_level)}
                                                {change.risk_level === 'high' ? '高' : change.risk_level === 'medium' ? '中' : '低'}
                                            </span>
                                            <span className="change-location">{change.location}</span>
                                        </div>
                                        {change.risk_reason && (
                                            <p className="risk-reason">{change.risk_reason}</p>
                                        )}
                                        {change.recommendation && (
                                            <div className="recommendation">
                                                <strong>提案:</strong> {change.recommendation}
                                            </div>
                                        )}
                                    </div>
                                ))}
                            </div>
                        )}
                    </section>

                    {/* AIからの提案 */}
                    {result.recommendations.length > 0 && (
                        <section className="recommendations-section card">
                            <h2>AIからの提案</h2>
                            <ul className="recommendations-list">
                                {result.recommendations.map((rec, index) => (
                                    <li key={index}>{rec}</li>
                                ))}
                            </ul>
                        </section>
                    )}

                    {/* 差分表示 */}
                    <section className="diff-section card">
                        <h2>
                            <FileText size={20} />
                            テキスト差分
                        </h2>
                        <div
                            className="diff-viewer"
                            dangerouslySetInnerHTML={{ __html: result.diff_html }}
                        />
                    </section>
                </div>
            )}
        </div>
    );
};

export default RedlineCompare;
