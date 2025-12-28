/**
 * LexFlow Protocol - コントラクトリストページ
 */
import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { FileText, Plus, Search, CheckCircle, Clock, ArrowUpRight } from 'lucide-react';
import { api } from '../services/api';
import type { Contract } from '../types';
import './Contracts.css';

// コントラクトページのコンポーネント
export function ContractsPage() {
    const [contracts, setContracts] = useState<Contract[]>([]);
    const [loading, setLoading] = useState(true);
    const [filter, setFilter] = useState<string>('all');
    const [search, setSearch] = useState('');

    // コントラクトの取得
    useEffect(() => {
        async function loadContracts() {
            try {
                const data = await api.getContracts();
                setContracts(data as Contract[]);
            } catch (error) {
                console.error('契約書の取得に失敗しました:', error);
            } finally {
                setLoading(false);
            }
        }
        loadContracts();
    }, []);

    // フィルターと検索の適用
    const filteredContracts = contracts.filter(c => {
        if (filter !== 'all' && c.status !== filter) return false;
        if (search && !c.title.toLowerCase().includes(search.toLowerCase())) return false;
        return true;
    });

    // 金額のフォーマット
    const formatCurrency = (value: number) => {
        return new Intl.NumberFormat('ja-JP', {
            style: 'currency',
            currency: 'JPY',
            maximumFractionDigits: 0,
        }).format(value);
    };

    // 日付のフォーマット
    const formatDate = (dateString: string) => {
        return new Date(dateString).toLocaleDateString('ja-JP', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
        });
    };

    // ステータスの表示
    const getStatusBadge = (status: string) => {
        switch (status) {
            case 'active':
                return <span className="badge badge-success"><CheckCircle size={12} /> Active</span>;
            case 'pending':
                return <span className="badge badge-warning"><Clock size={12} /> Pending</span>;
            case 'completed':
                return <span className="badge badge-info"><CheckCircle size={12} /> Completed</span>;
            default:
                return <span className="badge badge-neutral">{status}</span>;
        }
    };

    // プログレスバーの表示
    const getProgressPercent = (contract: Contract) => {
        if (contract.total_amount === 0) return 0;
        return (contract.released_amount / contract.total_amount) * 100;
    };

    return (
        <div className="contracts-page">
            <div className="page-header">
                <div>
                    <h1>契約書</h1>
                    <p>契約書の管理と追跡</p>
                </div>
                <Link to="/upload" className="btn btn-primary">
                    <Plus size={18} />
                    新規契約書
                </Link>
            </div>

            {/* フィルター */}
            <div className="filters-bar card">
                <div className="search-box">
                    <Search size={18} />
                    <input
                        type="text"
                        className="search-input"
                        placeholder="契約書を検索..."
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                    />
                </div>
                <div className="filter-tabs">
                    <button
                        className={`filter-tab ${filter === 'all' ? 'active' : ''}`}
                        onClick={() => setFilter('all')}
                    >
                        All ({contracts.length})
                    </button>
                    <button
                        className={`filter-tab ${filter === 'active' ? 'active' : ''}`}
                        onClick={() => setFilter('active')}
                    >
                        Active ({contracts.filter(c => c.status === 'active').length})
                    </button>
                    <button
                        className={`filter-tab ${filter === 'pending' ? 'active' : ''}`}
                        onClick={() => setFilter('pending')}
                    >
                        Pending ({contracts.filter(c => c.status === 'pending').length})
                    </button>
                    <button
                        className={`filter-tab ${filter === 'completed' ? 'active' : ''}`}
                        onClick={() => setFilter('completed')}
                    >
                        Completed ({contracts.filter(c => c.status === 'completed').length})
                    </button>
                </div>
            </div>

            {/* コントラクトグリッド */}
            {loading ? (
                <div className="loading-state">
                    <div className="spinner"></div>
                    <p>契約書の読み込み中...</p>
                </div>
            ) : filteredContracts.length === 0 ? (
                <div className="empty-state card">
                    <FileText size={48} />
                    <h3>契約書が見つかりませんでした</h3>
                    <p>{search ? '検索を調整してみてください' : '初めての契約書をアップロードしてみてください'}</p>
                    {!search && (
                        <Link to="/upload" className="btn btn-primary">
                            新規契約書
                        </Link>
                    )}
                </div>
            ) : (
                <div className="contracts-grid">
                    {filteredContracts.map(contract => (
                        <Link
                            key={contract.id}
                            to={`/contracts/${contract.id}`}
                            className="contract-card card"
                        >
                            <div className="contract-card-header">
                                <div className="contract-icon">
                                    <FileText size={24} />
                                </div>
                                {getStatusBadge(contract.status)}
                            </div>

                            <h3 className="contract-title">{contract.title}</h3>

                            <div className="contract-meta">
                                <div className="meta-item">
                                    <span className="meta-label">条件</span>
                                    <span className="meta-value">{contract.condition_count}</span>
                                </div>
                                <div className="meta-item">
                                    <span className="meta-label">金額</span>
                                    <span className="meta-value">{formatCurrency(contract.total_amount)}</span>
                                </div>
                            </div>

                            <div className="contract-progress">
                                <div className="progress-header">
                                    <span>発行</span>
                                    <span>{formatCurrency(contract.released_amount)}</span>
                                </div>
                                <div className="progress-bar">
                                    <div
                                        className="progress-bar-fill"
                                        style={{ width: `${getProgressPercent(contract)}%` }}
                                    ></div>
                                </div>
                            </div>

                            <div className="contract-footer">
                                <span className="text-muted text-sm">{formatDate(contract.created_at)}</span>
                                <span className="view-link">
                                    詳細 <ArrowUpRight size={14} />
                                </span>
                            </div>
                        </Link>
                    ))}
                </div>
            )}
        </div>
    );
}
