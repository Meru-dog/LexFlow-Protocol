/**
 * LexFlow Protocol - Header Component
 */
import { Link } from 'react-router-dom';
import { Wallet, ChevronDown, Zap } from 'lucide-react';
import { useWallet } from '../contexts/WalletContext';
import './Header.css';

export function Header() {
    const { isConnected, address, chainId, connect, isLoading } = useWallet();

    const formatAddress = (addr: string) => {
        return `${addr.slice(0, 6)}...${addr.slice(-4)}`;
    };

    const getNetworkName = (id: number | null) => {
        switch (id) {
            case 1: return 'Ethereum';
            case 11155111: return 'Sepolia';
            case 31337: return 'Localhost';
            default: return 'Unknown';
        }
    };

    return (
        <header className="header">
            <div className="header-content container">
                <Link to="/" className="logo">
                    <div className="logo-icon">
                        <Zap size={24} />
                    </div>
                    <span className="logo-text">LexFlow</span>
                    <span className="logo-badge">Protocol</span>
                </Link>

                <nav className="nav">
                    <Link to="/" className="nav-link">Home</Link>
                    <Link to="/dashboard" className="nav-link">Dashboard</Link>
                    <Link to="/contracts" className="nav-link">Contracts</Link>
                    <Link to="/verification" className="nav-link">Verification</Link>
                    <Link to="/upload" className="nav-link">Upload</Link>
                </nav>

                <div className="header-actions">
                    {isConnected ? (
                        <button className="wallet-btn connected">
                            <div className="status-dot online"></div>
                            <span className="network">{getNetworkName(chainId)}</span>
                            <span className="address">{formatAddress(address!)}</span>
                            <ChevronDown size={16} />
                        </button>
                    ) : (
                        <button
                            className="btn btn-primary"
                            onClick={connect}
                            disabled={isLoading}
                        >
                            <Wallet size={18} />
                            {isLoading ? 'Connecting...' : 'Connect Wallet'}
                        </button>
                    )}
                </div>
            </div>
        </header>
    );
}
