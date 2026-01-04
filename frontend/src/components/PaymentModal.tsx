import React, { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { X, CreditCard, ExternalLink, RefreshCw, CheckCircle } from 'lucide-react';

interface PaymentInfo {
    price: number;
    currency: string;
    network: string;
    recipient: string;
    token_address: string;
}

interface PaymentModalProps {
    isOpen: boolean;
    onClose: () => void;
    paymentInfo: PaymentInfo;
    onPaymentComplete: (txHash: string) => void;
}

export const PaymentModal: React.FC<PaymentModalProps> = ({ isOpen, onClose, paymentInfo, onPaymentComplete }) => {
    const [isProcessing, setIsProcessing] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [retryDelay, setRetryDelay] = useState(0);
    const [step, setStep] = useState<'initial' | 'processing' | 'success'>('initial');

    useEffect(() => {
        let timer: any;
        if (retryDelay > 0) {
            timer = setInterval(() => {
                setRetryDelay(prev => prev - 1);
            }, 1000);
        }
        return () => clearInterval(timer);
    }, [retryDelay]);

    if (!isOpen) return null;

    const handleSuccess = (txHash: string) => {
        // トランザクションハッシュを保存して再試行時に使えるようにする
        const cacheKey = `payment_sig_${window.location.pathname}`;
        localStorage.setItem(cacheKey, txHash);
        onPaymentComplete(txHash);
    };

    const handlePayment = async () => {
        if (isProcessing) return;
        setIsProcessing(true);
        setError(null);

        try {
            if (!(window as any).ethereum) {
                throw new Error("Metamaskがインストールされていません");
            }

            const ethereum = (window as any).ethereum;

            // 現在のチェーンIDを確認
            let currentChainId;
            try {
                currentChainId = await ethereum.request({ method: 'eth_chainId' });
            } catch (e) {
                console.warn("Failed to get current chain ID:", e);
                currentChainId = null;
            }

            // 既にSepoliaに接続している場合はスキップ
            if (currentChainId !== '0xaa36a7') {
                try {
                    await ethereum.request({
                        method: 'wallet_switchEthereumChain',
                        params: [{ chainId: '0xaa36a7' }], // Sepolia
                    });
                } catch (switchError: any) {
                    if (switchError.code === 4902) {
                        // ネットワークが登録されていない場合のみ追加
                        try {
                            await ethereum.request({
                                method: 'wallet_addEthereumChain',
                                params: [{
                                    chainId: '0xaa36a7',
                                    chainName: 'Sepolia Test Network',
                                    nativeCurrency: { name: 'Sepolia ETH', symbol: 'SepoliaETH', decimals: 18 },
                                    rpcUrls: ['https://rpc.sepolia.org', 'https://sepolia.public.blastapi.io'],
                                    blockExplorerUrls: ['https://sepolia.etherscan.io']
                                }],
                            });
                        } catch (addError) {
                            throw new Error("Sepoliaへの切り替えに失敗しました。Metamaskで手動設定を確認してください。");
                        }
                    } else if (switchError.code === 4001) {
                        // ユーザーがキャンセルした場合
                        throw new Error("ネットワーク切り替えがキャンセルされました");
                    } else if (switchError.code === -32002) {
                        throw new Error("MetaMaskでネットワーク切り替えのリクエストが進行中です。MetaMaskを確認してください。");
                    } else {
                        throw switchError;
                    }
                }
            }

            // アカウント取得の前に、既に接続されているか確認
            let accounts = [];
            try {
                accounts = await ethereum.request({ method: 'eth_accounts' });
            } catch (e) {
                console.warn("Failed to get accounts:", e);
            }

            if (accounts.length === 0) {
                try {
                    accounts = await ethereum.request({ method: 'eth_requestAccounts' });
                } catch (reqError: any) {
                    if (reqError.code === -32002) {
                        throw new Error("MetaMaskで接続リクエストが既に開いています。MetaMaskを確認してください。");
                    }
                    throw reqError;
                }
            }

            const account = accounts[0];

            // ERC20 Transfer Data
            const toAddress = paymentInfo.recipient.replace("0x", "");
            const amountWei = BigInt(Math.floor(paymentInfo.price * 10 ** 18)); // 小数点誤差を防ぐ
            const methodId = "0xa9059cbb"; // transfer(address,uint256)
            const data = methodId + toAddress.padStart(64, "0") + amountWei.toString(16).padStart(64, "0");

            let txHash;
            try {
                txHash = await ethereum.request({
                    method: 'eth_sendTransaction',
                    params: [{
                        from: account,
                        to: paymentInfo.token_address,
                        data: data,
                    }],
                });
            } catch (txError: any) {
                if (txError.code === -32002) {
                    throw new Error("MetaMaskで送信リクエストが既に開いています。MetaMaskを確認してください。");
                }
                throw txError;
            }

            // 成功状態へ移行
            setStep('success');
            setTimeout(() => {
                handleSuccess(txHash);
            }, 2000);

        } catch (err: any) {
            console.error("Payment Error:", err);
            let msg = err.message || "支払いに失敗しました";

            // -32603 (rate limited) も追加
            if (err.code === -32002 || err.code === -32603 || msg.includes("too many errors") || msg.toLowerCase().includes("rate limited") || msg.includes("already pending")) {
                msg = "RPC接続制限、またはMetaMaskの操作待ちです。MetaMaskウィンドウが最小化されていないか確認してください。リクエストが詰まっている場合は30秒ほど待ってから再試行してください。";
                setRetryDelay(15); // ちょっと短めにする
            }
            setError(msg);
        } finally {
            setIsProcessing(false);
        }
    };

    const modalContent = (
        <div className="payment-modal-overlay" style={{
            position: 'fixed',
            inset: 0,
            zIndex: 9999,
            backgroundColor: 'rgba(0, 0, 0, 0.6)',
            display: 'flex',
            alignItems: 'flex-start',
            justifyContent: 'center',
            paddingTop: '50px',
            overflowY: 'auto'
        }}>
            <div className="payment-modal-container" style={{
                backgroundColor: 'white',
                borderRadius: '12px',
                boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1)',
                width: '100%',
                maxWidth: '450px',
                padding: '24px',
                position: 'relative',
                margin: '16px'
            }}>
                {step !== 'success' && (
                    <button
                        onClick={onClose}
                        style={{ position: 'absolute', top: '16px', right: '16px', color: '#6b7280', border: 'none', background: 'none', cursor: 'pointer' }}
                    >
                        <X size={24} />
                    </button>
                )}

                {step === 'success' ? (
                    <div style={{ textAlign: 'center', padding: '24px 0' }}>
                        <div style={{ margin: '0 auto 16px', backgroundColor: '#dcfce7', width: '64px', height: '64px', borderRadius: '32px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                            <CheckCircle style={{ color: '#16a34a', margin: 'auto' }} size={40} />
                        </div>
                        <h2 style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#1f2937', margin: '0' }}>支払い完了！</h2>
                        <p style={{ color: '#4b5563', marginTop: '8px' }}>
                            トランザクションが送信されました。AI分析を開始します。
                        </p>
                    </div>
                ) : (
                    <>
                        <div style={{ textAlign: 'center', marginBottom: '24px' }}>
                            <div style={{ margin: '0 auto 16px', backgroundColor: '#dbeafe', width: '64px', height: '64px', borderRadius: '32px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                <CreditCard style={{ color: '#2563eb', margin: 'auto' }} size={32} />
                            </div>
                            <h2 style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#1f2937', margin: '0' }}>支払いが必要です</h2>
                            <p style={{ color: '#4b5563', marginTop: '8px' }}>
                                AI分析の実行には決済が必要です
                            </p>
                        </div>

                        <div style={{ backgroundColor: '#f9fafb', padding: '16px', borderRadius: '8px', marginBottom: '24px', border: '1px solid #e5e7eb' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                                <span style={{ color: '#4b5563' }}>サービス</span>
                                <span style={{ fontWeight: 600 }}>AI義務抽出</span>
                            </div>
                            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '1.25rem', fontWeight: 'bold', color: '#2563eb' }}>
                                <span>価格</span>
                                <span>{paymentInfo.price} {paymentInfo.currency}</span>
                            </div>
                        </div>

                        {error && (
                            <div style={{ backgroundColor: '#fef2f2', color: '#dc2626', padding: '12px', borderRadius: '6px', marginBottom: '16px', fontSize: '0.875rem' }}>
                                {error}
                                {retryDelay > 0 && (
                                    <div style={{ marginTop: '8px', fontWeight: 'bold' }}>
                                        再試行可能まで: {retryDelay}秒
                                    </div>
                                )}
                            </div>
                        )}

                        <button
                            onClick={handlePayment}
                            disabled={isProcessing || retryDelay > 0}
                            style={{
                                width: '100%',
                                backgroundColor: (isProcessing || retryDelay > 0) ? '#93c5fd' : '#2563eb',
                                color: 'white',
                                fontWeight: 'bold',
                                padding: '12px',
                                borderRadius: '8px',
                                border: 'none',
                                cursor: (isProcessing || retryDelay > 0) ? 'not-allowed' : 'pointer',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                transition: 'background-color 0.2s'
                            }}
                        >
                            {isProcessing ? (
                                <>
                                    <RefreshCw size={18} className="animate-spin" style={{ marginRight: '8px' }} />
                                    処理中...
                                </>
                            ) : (
                                <>
                                    ウォレットで支払う
                                    <ExternalLink size={18} style={{ marginLeft: '8px' }} />
                                </>
                            )}
                        </button>

                        <p style={{ fontSize: '0.75rem', color: '#9ca3af', textAlign: 'center', marginTop: '16px' }}>
                            SepoliaネットワークでJPYCを送金します
                        </p>
                    </>
                )}
            </div>
        </div>
    );

    return createPortal(modalContent, document.body);
};
