/**
 * LexFlow Protocol - コントラクトアップロードページ
 */
import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Upload, FileText, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';
import { useWallet } from '../contexts/WalletContext';
import { api } from '../services/api';
import './Upload.css';

// コントラクトアップロードページ
export function UploadPage() {
    const navigate = useNavigate(); // ページ遷移
    const { isConnected, address } = useWallet(); // ウォレット接続状態
    const [file, setFile] = useState<File | null>(null); // アップロードファイル
    const [dragOver, setDragOver] = useState(false); // ドラッグアンドドロップ状態
    const [title, setTitle] = useState(''); // コントラクトタイトル
    const [lawyerAddress, setLawyerAddress] = useState(''); // 弁護士アドレス
    const [totalAmount, setTotalAmount] = useState<string>(''); // 手動での総額指定
    const [loading, setLoading] = useState(false); // ロード状態
    const [error, setError] = useState<string | null>(null); // エラー
    const [result, setResult] = useState<any>(null); // 結果

    // ドラッグアンドドロップ
    const handleDragOver = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        setDragOver(true);
    }, []);

    // ドラッグアンドドロップ
    const handleDragLeave = useCallback(() => {
        setDragOver(false);
    }, []);

    // ドラッグアンドドロップ
    const handleDrop = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        setDragOver(false);
        const droppedFile = e.dataTransfer.files[0];
        if (droppedFile) {
            const validTypes = ['application/pdf', 'text/plain', 'text/markdown'];
            // Check extension as well since some systems might not set MIME type correctly for .md
            const isMd = droppedFile.name.endsWith('.md');
            if (validTypes.includes(droppedFile.type) || isMd) {
                setFile(droppedFile);
                setError(null);
            } else {
                setError('PDF、テキスト(.txt)、またはMarkdown(.md)ファイルをアップロードして下さい。');
            }
        }
    }, []);

    // ファイル選択
    const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
        const selectedFile = e.target.files?.[0];
        if (selectedFile) {
            const validTypes = ['application/pdf', 'text/plain', 'text/markdown'];
            const isMd = selectedFile.name.endsWith('.md');
            if (validTypes.includes(selectedFile.type) || isMd) {
                setFile(selectedFile);
                setError(null);
            } else {
                setError('PDF、テキスト(.txt)、またはMarkdown(.md)ファイルをアップロードして下さい。');
            }
        }
    }, []);

    // コントラクトアップロード
    const handleUpload = async () => {
        if (!file) return;

        if (!lawyerAddress) {
            setError('弁護士アドレスは契約の有効化に必須です。');
            return;
        }

        if (!/^0x[a-fA-F0-9]{40}$/.test(lawyerAddress)) {
            setError('弁護士アドレスは有効な形式で入力して下さい。');
            return;
        }

        setLoading(true);
        setError(null);

        try {
            const data = await api.uploadContract(
                file,
                title || undefined,
                address || undefined,
                lawyerAddress,
                totalAmount ? parseFloat(totalAmount) : undefined
            );
            setResult(data);
        } catch (err: any) {
            setError(err.message || '契約のアップロードに失敗しました。');
        } finally {
            setLoading(false);
        }
    };

    // ファイルサイズフォーマット
    const formatFileSize = (bytes: number) => {
        if (bytes < 1024) return `${bytes} B`;
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
        return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    };

    if (result) {
        return (
            <div className="upload-page">
                <div className="upload-success glass-card">
                    <div className="success-icon">
                        <CheckCircle size={48} />
                    </div>
                    <h2>契約解析に成功しました！</h2>
                    <p>AIが契約を解析し、以下の情報を抽出しました：</p>

                    <div className="parsed-summary">
                        <div className="summary-item">
                            <span className="label">タイトル</span>
                            <span className="value">{result.title}</span>
                        </div>
                        <div className="summary-item">
                            <span className="label">当事者</span>
                            <span className="value">{result.parties?.join(', ') || 'N/A'}</span>
                        </div>
                        <div className="summary-item">
                            <span className="label">節数</span>
                            <span className="value">{result.clauses?.length || 0}</span>
                        </div>
                        <div className="summary-item">
                            <span className="label">総額</span>
                            <span className="value highlight">
                                {new Intl.NumberFormat('ja-JP', { style: 'currency', currency: 'JPY' })
                                    .format(result.total_value || 0)}
                            </span>
                        </div>
                    </div>

                    <div className="summary-box">
                        <h4>要約</h4>
                        <p>{result.summary}</p>
                    </div>

                    <div className="success-actions">
                        <button
                            className="btn btn-primary btn-lg"
                            onClick={() => navigate(`/contracts/${result.contract_id}`)}
                        >
                            契約詳細を見る
                        </button>
                        <button
                            className="btn btn-secondary"
                            onClick={() => {
                                setResult(null);
                                setFile(null);
                                setTitle('');
                                setLawyerAddress('');
                            }}
                        >
                            他の契約書をアップロードする
                        </button>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="upload-page">
            <div className="upload-container">
                <div className="upload-header">
                    <h1>契約書をアップロード</h1>
                    <p>契約書(PDF/Text/Markdown)をアップロードしてAIで自動解析し、ブロックチェーンに登録します</p>
                </div>

                <div className="upload-content">
                    {/* アップデートゾーン */}
                    <div
                        className={`upload-zone ${dragOver ? 'drag-over' : ''} ${file ? 'has-file' : ''}`}
                        onDragOver={handleDragOver}
                        onDragLeave={handleDragLeave}
                        onDrop={handleDrop}
                    >
                        {file ? (
                            <div className="file-preview">
                                <div className="file-icon">
                                    <FileText size={48} />
                                </div>
                                <div className="file-info">
                                    <span className="file-name">{file.name}</span>
                                    <span className="file-size">{formatFileSize(file.size)}</span>
                                </div>
                                <button
                                    className="btn btn-ghost btn-sm"
                                    onClick={() => setFile(null)}
                                >
                                    削除
                                </button>
                            </div>
                        ) : (
                            <>
                                <div className="upload-icon">
                                    <Upload size={48} />
                                </div>
                                <h3>ファイルをここにドラッグ&ドロップ</h3>
                                <p>またはクリックしてファイルを選択</p>
                                <input
                                    type="file"
                                    accept=".pdf,.txt,.md"
                                    onChange={handleFileSelect}
                                    className="file-input"
                                />
                            </>
                        )}
                    </div>

                    {/* コントラクト詳細 */}
                    <div className="upload-form card">
                        <h3>契約詳細</h3>

                        <div className="input-group">
                            <label className="input-label">契約タイトル（任意）</label>
                            <input
                                type="text"
                                className="input"
                                placeholder="契約タイトルを入力..."
                                value={title}
                                onChange={(e) => setTitle(e.target.value)}
                            />
                        </div>

                        <div className="input-group">
                            <label className="input-label">総額 JPYC（任意）</label>
                            <input
                                type="number"
                                className="input"
                                placeholder="総額を入力（例: 10000）..."
                                value={totalAmount}
                                onChange={(e) => setTotalAmount(e.target.value)}
                            />
                            <span className="input-hint">空欄の場合、AIがPDFから金額を抽出します</span>
                        </div>

                        <div className="input-group">
                            <label className="input-label">弁護士アドレス <span className="text-error">*必須</span></label>
                            <input
                                type="text"
                                className="input font-mono"
                                placeholder="0x..."
                                value={lawyerAddress}
                                onChange={(e) => setLawyerAddress(e.target.value)}
                                required
                            />
                            <span className="input-hint">条件を承認する弁護士のウォレットアドレスです。ブロックチェーン有効化に必要です</span>
                        </div>

                        {isConnected && (
                            <div className="connected-wallet">
                                <span className="label">接続中のウォレット（支払者）</span>
                                <span className="address font-mono">{address}</span>
                            </div>
                        )}

                        {error && (
                            <div className="error-message">
                                <AlertCircle size={16} />
                                {error}
                            </div>
                        )}

                        <button
                            className="btn btn-primary btn-lg upload-btn"
                            onClick={handleUpload}
                            disabled={!file || loading}
                        >
                            {loading ? (
                                <>
                                    <Loader2 size={20} className="spinner-icon" />
                                    契約書を解析中...
                                </>
                            ) : (
                                <>
                                    <Upload size={20} />
                                    アップロードして解析
                                </>
                            )}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
