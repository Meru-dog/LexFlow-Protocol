/**
 * LexFlow Protocol - ダッシュボードページ
 */
import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
    FileText,
    CheckCircle,
    Clock,
    DollarSign,
    ArrowUpRight,
    TrendingUp,
    Zap,
    Shield
} from 'lucide-react';
import { useWallet } from '../contexts/WalletContext';
import { api } from '../services/api';
import type { Contract, BlockchainStatus } from '../types';
import './Dashboard.css';

// ダッシュボードページのコンポーネント
export function Dashboard() {
    useWallet(); // ウォレット状態のフック
    const [contracts, setContracts] = useState<Contract[]>([]); // コントラクトの状態
    const [blockchainStatus, setBlockchainStatus] = useState<BlockchainStatus | null>(null); // ブロックチェーンの状態
    const [loading, setLoading] = useState(true); // ロード状態

    // データの取得
    useEffect(() => {
        async function loadData() {
            try {
                const [contractsData, statusData] = await Promise.all([
                    api.getContracts(),
                    api.getBlockchainStatus(),
                ]);
                setContracts(contractsData as Contract[]);
                setBlockchainStatus(statusData as BlockchainStatus);
            } catch (error) {
                console.error('Failed to load data:', error);
            } finally {
                setLoading(false);
            }
        }
        loadData();
    }, []);

    // データの統計
    const stats = {
        totalContracts: contracts.length,
        activeContracts: contracts.filter(c => c.status === 'active').length,
        completedContracts: contracts.filter(c => c.status === 'completed').length,
        totalValue: contracts.reduce((sum, c) => sum + c.total_amount, 0),
    };

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

    // コンテキストのステータス
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

    return (
        <div className="dashboard">
            {/* Hero Section */}
            <section className="hero">
                <div className="hero-content">
                    <h1 className="hero-title">
                        <span className="gradient-text">AI-Powered</span> Contract Execution
                    </h1>
                    <p className="hero-subtitle">
                        AI判定とEthereumスマートコントラクトを用いて契約の条件を自動的に満たし、
                        JPYCを自動的に支払う
                    </p>
                    <div className="hero-actions">
                        <Link to="/upload" className="btn btn-primary btn-lg">
                            <FileText size={20} />
                            契約書のアップロード
                        </Link>
                        <Link to="/contracts" className="btn btn-secondary btn-lg">
                            すべての契約書をみる
                        </Link>
                    </div>
                </div>
                <div className="hero-visual">
                    <div className="hero-card glass-card">
                        <div className="hero-icon">
                            <Zap size={48} />
                        </div>
                        <h3>Smart Escrow</h3>
                        <p>Condition-based JPYC payments</p>
                    </div>
                </div>
            </section>

            {/* 統計グリッド */}
            <section className="stats-section">
                <div className="grid grid-cols-4 gap-6">
                    <div className="stat-card">
                        <div className="stat-icon">
                            <FileText size={24} />
                        </div>
                        <div className="stat-value">{stats.totalContracts}</div>
                        <div className="stat-label">総契約数</div>
                    </div>
                    <div className="stat-card">
                        <div className="stat-icon active">
                            <TrendingUp size={24} />
                        </div>
                        <div className="stat-value">{stats.activeContracts}</div>
                        <div className="stat-label">アクティブ</div>
                    </div>
                    <div className="stat-card">
                        <div className="stat-icon success">
                            <CheckCircle size={24} />
                        </div>
                        <div className="stat-value">{stats.completedContracts}</div>
                        <div className="stat-label">完了</div>
                    </div>
                    <div className="stat-card">
                        <div className="stat-icon money">
                            <DollarSign size={24} />
                        </div>
                        <div className="stat-value">{formatCurrency(stats.totalValue)}</div>
                        <div className="stat-label">総額</div>
                    </div>
                </div>
            </section>

            {/* 最近のコントラクト */}
            <section className="recent-section">
                <div className="section-header">
                    <h2>最近の契約</h2>
                    <Link to="/contracts" className="btn btn-ghost">
                        すべて表示 <ArrowUpRight size={16} />
                    </Link>
                </div>

                {loading ? (
                    <div className="loading-state">
                        <div className="spinner"></div>
                        <p>ロード中...</p>
                    </div>
                ) : contracts.length === 0 ? (
                    <div className="empty-state card">
                        <FileText size={48} />
                        <h3>まだ契約はありません</h3>
                        <p>最初の契約をアップロードして始めてください。</p>
                        <Link to="/upload" className="btn btn-primary">
                            契約書のアップロード
                        </Link>
                    </div>
                ) : (
                    <div className="contracts-table card">
                        <table className="table">
                            <thead>
                                <tr>
                                    <th>契約書</th>
                                    <th>状態</th>
                                    <th>条件</th>
                                    <th>価格</th>
                                    <th>作成日</th>
                                    <th></th>
                                </tr>
                            </thead>
                            <tbody>
                                {contracts.slice(0, 5).map(contract => (
                                    <tr key={contract.id}>
                                        <td>
                                            <div className="contract-name">
                                                <FileText size={16} />
                                                <span>{contract.title}</span>
                                            </div>
                                        </td>
                                        <td>{getStatusBadge(contract.status)}</td>
                                        <td>{contract.condition_count}</td>
                                        <td className="font-mono">{formatCurrency(contract.total_amount)}</td>
                                        <td className="text-muted">{formatDate(contract.created_at)}</td>
                                        <td>
                                            <Link to={`/contracts/${contract.id}`} className="btn btn-ghost btn-sm">
                                                View <ArrowUpRight size={14} />
                                            </Link>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </section>

            {/* ブロックチェーンのステータス */}
            <section className="status-section">
                <div className="card">
                    <div className="card-header">
                        <h3 className="card-title">
                            <Shield size={20} />
                            ブロックチェーンのステータス
                        </h3>
                        <div className={`status-indicator ${blockchainStatus?.connected ? 'online' : 'offline'}`}>
                            <div className="status-dot"></div>
                            {blockchainStatus?.connected ? '接続中' : '切断中'}
                        </div>
                    </div>
                    {blockchainStatus && (
                        <div className="status-details">
                            <div className="status-item">
                                <span className="status-label">ネットワーク</span>
                                <span className="status-value font-mono">
                                    {blockchainStatus.chain_id === 11155111 ? 'Sepolia Testnet' :
                                        blockchainStatus.chain_id === 1 ? 'Ethereum Mainnet' :
                                            `Chain ID: ${blockchainStatus.chain_id}`}
                                </span>
                            </div>
                            <div className="status-item">
                                <span className="status-label">エスクロー契約</span>
                                <span className="status-value font-mono truncate">
                                    {blockchainStatus.escrow_address || 'デプロイされていません。'}
                                </span>
                            </div>
                        </div>
                    )}
                </div>
            </section>
        </div>
    );
}
