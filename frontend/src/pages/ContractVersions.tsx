import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { History, Plus, FileText, Clock, PenTool, ArrowLeft, GitCompareArrows, ExternalLink } from 'lucide-react';
import { api, getFileUrl } from '../services/api';
import { SignatureModal } from '../components/SignatureModal';
import './ContractVersions.css';

interface Version {
    id: string;
    case_id: string;
    version: number;
    doc_hash: string;
    file_url: string;
    title: string;
    summary: string;
    status: string;
    created_at: string;
}

const ContractVersions: React.FC = () => {
    const { contractId } = useParams<{ contractId: string }>();
    const [versions, setVersions] = useState<Version[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // モーダル状態
    const [isUploadOpen, setIsUploadOpen] = useState(false);
    const [isSignatureOpen, setIsSignatureOpen] = useState(false);
    const [selectedVersion, setSelectedVersion] = useState<Version | null>(null);

    // アップロード用
    const [uploadFile, setUploadFile] = useState<File | null>(null);
    const [uploadTitle, setUploadTitle] = useState("");
    const [isUploading, setIsUploading] = useState(false);

    useEffect(() => {
        if (contractId) {
            loadVersions();
        }
    }, [contractId]);

    const loadVersions = async () => {
        try {
            setLoading(true);
            const data = await api.getVersionsByCase(contractId!);
            setVersions(data as Version[]);
        } catch (err: any) {
            setError(err.message || "Failed to load versions");
            console.error(error); // Use it to satisfy lint if needed, or just remove error state if unused
        } finally {
            setLoading(false);
        }
    };

    const handleUpload = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!uploadFile || !contractId) return;

        setIsUploading(true);
        try {
            // モックのクリエイターアドレス
            const creator = "0x1234567890123456789012345678901234567890";
            await api.createVersion(contractId, uploadFile, uploadTitle || uploadFile.name, creator);
            setIsUploadOpen(false);
            setUploadFile(null);
            setUploadTitle("");
            await loadVersions();
        } catch (err: any) {
            alert(err.message || "Upload failed");
        } finally {
            setIsUploading(false);
        }
    };

    const formatDate = (dateString: string) => {
        return new Date(dateString).toLocaleString('ja-JP');
    };

    if (loading) return <div className="loading">読み込み中...</div>;

    return (
        <div className="versions-page">
            <header className="page-header">
                <Link to={`/contracts/${contractId}`} className="back-link">
                    <ArrowLeft size={18} /> 契約詳細へ戻る
                </Link>
                <div className="header-main">
                    <div className="title-group">
                        <History size={32} />
                        <div>
                            <h1>契約版管理 / 署名</h1>
                            <p>すべてのバージョンの変更履歴と法的な署名状況</p>
                        </div>
                    </div>
                    <div className="header-actions">
                        <Link to={`/contracts/${contractId}/redline`} className="btn btn-secondary">
                            <GitCompareArrows size={18} /> Redline比較
                        </Link>
                        <button className="btn btn-primary" onClick={() => setIsUploadOpen(true)}>
                            <Plus size={18} /> 新しい版をアップロード
                        </button>
                    </div>
                </div>
            </header>

            <div className="versions-list">
                {versions.length === 0 ? (
                    <div className="empty-versions">
                        <FileText size={48} />
                        <p>まだ版が登録されていません</p>
                    </div>
                ) : (
                    versions.map((v) => (
                        <div key={v.id} className={`version-card ${v.status}`}>
                            <div className="version-badge">Ver.{v.version}</div>
                            <div className="version-content">
                                <div className="version-header">
                                    <h3>{v.title}</h3>
                                    <div className="version-header-actions flex items-center gap-2">
                                        <a
                                            href={getFileUrl(v.file_url)}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            className="text-sm text-primary hover:text-primary-focus bg-neutral px-3 py-1 rounded-full flex items-center gap-1 transition-colors font-medium "
                                        >
                                            ファイルを表示 <ExternalLink size={12} />
                                        </a>
                                        <span className={`status-badge ${v.status}`}>
                                            {v.status === 'signed' ? '署名済み' : '要署名'}
                                        </span>
                                    </div>
                                </div>
                                <p className="version-summary">{v.summary || "概要なし"}</p>
                                <div className="version-meta">
                                    <div className="meta-item">
                                        <Clock size={14} />
                                        <span>作成: {formatDate(v.created_at)}</span>
                                    </div>
                                    <div className="meta-item hash">
                                        <span>HASH: {v.doc_hash.substring(0, 16)}...</span>
                                    </div>
                                </div>
                            </div>
                            <div className="version-actions">
                                {v.status !== 'signed' && (
                                    <button
                                        className="btn btn-primary btn-sm"
                                        onClick={() => {
                                            setSelectedVersion(v);
                                            setIsSignatureOpen(true);
                                        }}
                                    >
                                        <PenTool size={16} /> 署名する
                                    </button>
                                )}
                            </div>
                        </div>
                    ))
                )}
            </div>

            {/* アップロードモーダル */}
            {isUploadOpen && (
                <div className="modal-overlay">
                    <div className="modal-content card">
                        <h3>新しい版のアップロード</h3>
                        <form onSubmit={handleUpload}>
                            <div className="form-group">
                                <label>タイトル / 変更内容の要約</label>
                                <input
                                    type="text"
                                    className="input"
                                    placeholder="例: 第2回ドラフト(修正後)"
                                    value={uploadTitle}
                                    onChange={e => setUploadTitle(e.target.value)}
                                    required
                                />
                            </div>
                            <div className="form-group">
                                <label>契約書ファイル (PDF, TXT, MD)</label>
                                <div className="file-input-wrapper">
                                    <input
                                        type="file"
                                        accept=".pdf,.txt,.md"
                                        onChange={e => setUploadFile(e.target.files?.[0] || null)}
                                        required
                                    />
                                </div>
                            </div>
                            <div className="modal-actions">
                                <button type="submit" className="btn btn-primary" disabled={isUploading}>
                                    {isUploading ? "アップロード中..." : "保存"}
                                </button>
                                <button type="button" className="btn btn-ghost" onClick={() => setIsUploadOpen(false)}>
                                    キャンセル
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {/* 署名モーダル */}
            {selectedVersion && (
                <SignatureModal
                    isOpen={isSignatureOpen}
                    onClose={() => setIsSignatureOpen(false)}
                    versionInfo={selectedVersion}
                    role="Legal Representative"
                    onSignatureComplete={loadVersions}
                />
            )}
        </div>
    );
};

export default ContractVersions;
