/**
 * LexFlow Protocol - Wallet Context
 * MetaMask wallet connection and state management
 */
import { createContext, useContext, useState, useCallback, useEffect, type ReactNode } from 'react';
import { BrowserProvider, JsonRpcSigner } from 'ethers';

interface WalletState {
    isConnected: boolean;
    address: string | null;
    chainId: number | null;
    provider: BrowserProvider | null;
    signer: JsonRpcSigner | null;
}

interface WalletContextType extends WalletState {
    connect: () => Promise<void>;
    disconnect: () => void;
    switchToSepolia: () => Promise<void>;
    isLoading: boolean;
    error: string | null;
}

const WalletContext = createContext<WalletContextType | null>(null);

const SEPOLIA_CHAIN_ID = 11155111;

export function WalletProvider({ children }: { children: ReactNode }) {
    const [state, setState] = useState<WalletState>({
        isConnected: false,
        address: null,
        chainId: null,
        provider: null,
        signer: null,
    });
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const connect = useCallback(async () => {
        if (typeof window.ethereum === 'undefined') {
            setError('MetaMask is not installed. Please install MetaMask.');
            return;
        }

        setIsLoading(true);
        setError(null);

        try {
            const provider = new BrowserProvider(window.ethereum);
            const accounts = await provider.send('eth_requestAccounts', []);
            const network = await provider.getNetwork();
            const signer = await provider.getSigner();

            setState({
                isConnected: true,
                address: accounts[0],
                chainId: Number(network.chainId),
                provider,
                signer,
            });
        } catch (err: any) {
            setError(err.message || 'Failed to connect wallet');
        } finally {
            setIsLoading(false);
        }
    }, []);

    const disconnect = useCallback(() => {
        setState({
            isConnected: false,
            address: null,
            chainId: null,
            provider: null,
            signer: null,
        });
    }, []);

    const switchToSepolia = useCallback(async () => {
        if (!window.ethereum) return;

        try {
            await window.ethereum.request({
                method: 'wallet_switchEthereumChain',
                params: [{ chainId: `0x${SEPOLIA_CHAIN_ID.toString(16)}` }],
            });
        } catch (switchError: any) {
            // Chain not added, add it
            if (switchError.code === 4902) {
                await window.ethereum.request({
                    method: 'wallet_addEthereumChain',
                    params: [{
                        chainId: `0x${SEPOLIA_CHAIN_ID.toString(16)}`,
                        chainName: 'Sepolia Testnet',
                        nativeCurrency: { name: 'SepoliaETH', symbol: 'ETH', decimals: 18 },
                        rpcUrls: ['https://sepolia.infura.io/v3/'],
                        blockExplorerUrls: ['https://sepolia.etherscan.io'],
                    }],
                });
            }
        }
    }, []);

    // Listen for account changes
    useEffect(() => {
        if (!window.ethereum) return;

        const handleAccountsChanged = (accounts: string[]) => {
            if (accounts.length === 0) {
                disconnect();
            } else {
                setState(prev => ({ ...prev, address: accounts[0] }));
            }
        };

        const handleChainChanged = (chainId: string) => {
            setState(prev => ({ ...prev, chainId: parseInt(chainId, 16) }));
        };

        window.ethereum.on('accountsChanged', handleAccountsChanged);
        window.ethereum.on('chainChanged', handleChainChanged);

        return () => {
            window.ethereum.removeListener('accountsChanged', handleAccountsChanged);
            window.ethereum.removeListener('chainChanged', handleChainChanged);
        };
    }, [disconnect]);

    // Auto-connect if previously connected
    useEffect(() => {
        if (window.ethereum) {
            window.ethereum.request({ method: 'eth_accounts' }).then((accounts: string[]) => {
                if (accounts.length > 0) {
                    connect();
                }
            });
        }
    }, []);

    return (
        <WalletContext.Provider value={{ ...state, connect, disconnect, switchToSepolia, isLoading, error }}>
            {children}
        </WalletContext.Provider>
    );
}

export function useWallet() {
    const context = useContext(WalletContext);
    if (!context) {
        throw new Error('useWallet must be used within a WalletProvider');
    }
    return context;
}

// Extend window for TypeScript
declare global {
    interface Window {
        ethereum?: any;
    }
}
