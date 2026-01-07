import React, { useState, useEffect } from 'react';
import { Search, FileText, ChevronRight, Loader2 } from 'lucide-react';
import { api, API_BASE } from '../services/api';
import './ContractSearch.css';

interface SearchResult {
    content: string;
    metadata: {
        contract_id: string;
        title?: string;
        workspace_id: string;
    };
    score: number;
}

const ContractSearch: React.FC = () => {
    const [query, setQuery] = useState('');
    const [results, setResults] = useState<SearchResult[]>([]);
    const [loading, setLoading] = useState(false);
    const [workspaces, setWorkspaces] = useState<any[]>([]);
    const [selectedWorkspaceId, setSelectedWorkspaceId] = useState<string>('');
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const loadWorkspaces = async () => {
            setError(null);
            try {
                const data = await api.getWorkspaces();
                setWorkspaces(data);
                if (data && data.length > 0) {
                    setSelectedWorkspaceId(data[0].id);
                } else {
                    // ワークスペースがない場合はエラーメッセージを表示
                    setError('ワークスペースが見つかりません。契約書をアップロードするワークスペースが必要です。');
                }
            } catch (err: any) {
                console.error('ワークスペースの読み込みに失敗しました。', err);
                if (err.message.includes('401') || err.message.includes('無効なトークン')) {
                    setError('セッションが期限切れです。一度ログアウトして再度ログインしてください。');
                } else {
                    setError('ワークスペースの読み込みに失敗しました。サーバーの状態を確認してください。');
                }
            }
        };
        loadWorkspaces();
    }, []);

    const handleSearch = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!query.trim() || !selectedWorkspaceId) return;

        setLoading(true);
        setError(null);
        try {
            const token = localStorage.getItem('access_token');
            const response = await fetch(`${API_BASE}/rag/search`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    query,
                    workspace_id: selectedWorkspaceId,
                    limit: 10
                })
            });

            if (!response.ok) {
                if (response.status === 401) {
                    throw new Error('セッションが期限切れです。再ログインしてください。');
                }
                throw new Error('検索中にエラーが発生しました');
            }
            const data = await response.json();
            setResults(data);
            if (data.length === 0) {
                setError('関連する情報が見つかりませんでした。別の言葉で試してみてください。');
            }
        } catch (err: any) {
            setError(err.message || '検索中にエラーが発生しました');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="search-container">
            <div className="search-header">
                <h1>契約アシスタント (RAG検索)</h1>
                <p>全ての契約書から必要な条項や条件を瞬時に発見します。</p>
            </div>

            <div className="search-controls">
                <select
                    value={selectedWorkspaceId}
                    onChange={(e) => setSelectedWorkspaceId(e.target.value)}
                    className="workspace-select"
                >
                    {workspaces.map(ws => (
                        <option key={ws.id} value={ws.id}>{ws.name}</option>
                    ))}
                </select>

                <form onSubmit={handleSearch} className="search-form">
                    <div className="search-input-wrapper">
                        <Search className="search-icon" size={20} />
                        <input
                            type="text"
                            value={query}
                            onChange={(e) => setQuery(e.target.value)}
                            placeholder="例: 損害賠償の上限について教えてください"
                            className="search-input"
                        />
                    </div>
                    <button type="submit" disabled={loading} className="search-button">
                        {loading ? <Loader2 className="animate-spin" /> : '検索'}
                    </button>
                </form>
            </div>

            {error && <div className="search-error">{error}</div>}

            <div className="search-results">
                {results.length > 0 ? (
                    results.map((result, index) => (
                        <div key={index} className="result-card">
                            <div className="result-metadata">
                                <FileText size={16} />
                                <span className="contract-title">{result.metadata.title || '無題の契約'}</span>
                                <span className="relevance-score">関連度: {(100 / (1 + result.score)).toFixed(1)}%</span>
                            </div>
                            <div className="result-content">
                                {result.content}
                            </div>
                            <div className="result-footer">
                                <a href={`/contracts/${result.metadata.contract_id}`} className="view-link">
                                    契約詳細を表示 <ChevronRight size={14} />
                                </a>
                            </div>
                        </div>
                    ))
                ) : !loading && query && (
                    <div className="no-results">
                        検索結果が見つかりませんでした。別のキーワードを試してください。
                    </div>
                )}
            </div>
        </div>
    );
};

export default ContractSearch;
