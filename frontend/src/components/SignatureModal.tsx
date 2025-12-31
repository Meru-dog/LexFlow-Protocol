import React, { useState } from 'react';
import { createPortal } from 'react-dom';
import { X, PenTool, CheckCircle, RefreshCw, AlertTriangle } from 'lucide-react';
import { api } from '../services/api';

interface VersionInfo {
    id: string;
    case_id: string;
    version: number;
    doc_hash: string;
    title: string;
}

interface SignatureModalProps {
    isOpen: boolean;
    onClose: () => void;
    versionInfo: VersionInfo;
    role: string;
    onSignatureComplete: () => void;
}

export const SignatureModal: React.FC<SignatureModalProps> = ({ isOpen, onClose, versionInfo, role, onSignatureComplete }) => {
    const [isProcessing, setIsProcessing] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [step, setStep] = useState<'initial' | 'processing' | 'success'>('initial');
    const [config, setConfig] = useState<{ chainId: number, escrowAddress: string } | null>(null);

    React.useEffect(() => {
        const loadConfig = async () => {
            try {
                const cfg = await api.getConfig();
                setConfig(cfg);
            } catch (err) {
                console.error("Failed to load signature config:", err);
                setError("署名設定の取得に失敗しました。");
            }
        };
        loadConfig();
    }, []);

    if (!isOpen) return null;

    const handleSign = async () => {
        if (isProcessing || !config) return;
        setIsProcessing(true);
        setError(null);

        try {
            if (!(window as any).ethereum) {
                throw new Error("Metamaskがインストールされていません");
            }

            const ethereum = (window as any).ethereum;
            const accounts = await ethereum.request({ method: 'eth_requestAccounts' });
            const account = accounts[0];
            const timestamp = Math.floor(Date.now() / 1000);

            // EIP-712 署名データ
            const domain = {
                name: "LexFlow Protocol",
                version: "1",
                chainId: config.chainId,
                verifyingContract: config.escrowAddress
            };

            const types = {
                ContractVersion: [
                    { name: "caseId", type: "string" },
                    { name: "version", type: "uint256" },
                    { name: "docHash", type: "bytes32" },
                    { name: "timestamp", type: "uint256" }
                ]
            };

            const message = {
                caseId: String(versionInfo.case_id),
                version: Number(versionInfo.version),
                docHash: String(versionInfo.doc_hash),
                timestamp: Number(timestamp)
            };

            const msgParams = JSON.stringify({
                domain,
                message,
                primaryType: "ContractVersion",
                types: {
                    EIP712Domain: [
                        { name: "name", type: "string" },
                        { name: "version", type: "string" },
                        { name: "chainId", type: "uint256" },
                        { name: "verifyingContract", type: "address" }
                    ],
                    ...types
                }
            });

            console.log("Signing Domain:", domain);
            console.log("Signing Message:", message);

            const signature = await ethereum.request({
                method: 'eth_signTypedData_v4',
                params: [account, msgParams],
            });

            console.log("Signature Generated:", signature);

            // バックエンドへ送信
            await api.submitSignature({
                version_id: versionInfo.id,
                signer: account,
                role: role,
                signature: signature,
                timestamp: timestamp
            });

            setStep('success');
            setTimeout(() => {
                onSignatureComplete();
                onClose();
            }, 2500);

        } catch (err: any) {
            console.error("Signature Error:", err);
            // エラーオブジェクトそのものを文字列化または詳細メッセージを表示
            const detailMsg = typeof err.message === 'string' ? err.message : JSON.stringify(err);
            setError(detailMsg || "署名に失敗しました。ユーザーによりキャンセルされたか、通信エラーの可能性があります。");
        } finally {
            setIsProcessing(false);
        }
    };

    const modalContent = (
        <div className="modal-overlay" style={{
            position: 'fixed',
            inset: 0,
            zIndex: 9999,
            backgroundColor: 'rgba(0, 0, 0, 0.6)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '16px'
        }}>
            <div className="modal-container" style={{
                backgroundColor: 'white',
                borderRadius: '12px',
                width: '100%',
                maxWidth: '480px',
                padding: '32px',
                position: 'relative',
                boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)'
            }}>
                {step !== 'success' && (
                    <button
                        onClick={onClose}
                        style={{ position: 'absolute', top: '20px', right: '20px', color: '#9ca3af', border: 'none', background: 'none', cursor: 'pointer' }}
                    >
                        <X size={24} />
                    </button>
                )}

                {step === 'success' ? (
                    <div style={{ textAlign: 'center', padding: '16px 0' }}>
                        <div style={{ margin: '0 auto 24px', backgroundColor: '#ecfdf5', width: '80px', height: '80px', borderRadius: '40px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                            <CheckCircle style={{ color: '#10b981' }} size={48} />
                        </div>
                        <h2 style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#111827', marginBottom: '8px' }}>署名完了</h2>
                        <p style={{ color: '#6b7280' }}>
                            デジタル署名が正常に記録されました。<br />このドキュメントの非改ざん性が保証されました。
                        </p>
                    </div>
                ) : (
                    <>
                        <div style={{ textAlign: 'center', marginBottom: '24px' }}>
                            <div style={{ margin: '0 auto 16px', backgroundColor: '#eef2ff', width: '64px', height: '64px', borderRadius: '32px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                <PenTool style={{ color: '#4f46e5' }} size={32} />
                            </div>
                            <h2 style={{ fontSize: '1.25rem', fontWeight: 'bold', color: '#111827' }}>デジタル署名の実行</h2>
                            <p style={{ color: '#6b7280', fontSize: '0.925rem', marginTop: '4px' }}>
                                EIP-712規格に基づき、ドキュメントの完全性を署名します
                            </p>
                        </div>

                        <div style={{ backgroundColor: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '8px', padding: '16px', marginBottom: '24px' }}>
                            <h3 style={{ fontSize: '0.875rem', fontWeight: '600', color: '#475569', marginBottom: '12px', borderBottom: '1px solid #e2e8f0', paddingBottom: '8px' }}>署名対象データ</h3>
                            <div style={{ fontSize: '0.875rem', display: 'grid', gap: '8px' }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                    <span style={{ color: '#64748b' }}>案件名</span>
                                    <span style={{ color: '#1e293b', fontWeight: '500' }}>{versionInfo.title}</span>
                                </div>
                                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                    <span style={{ color: '#64748b' }}>バージョン</span>
                                    <span style={{ color: '#1e293b', fontWeight: '500' }}>Ver.{versionInfo.version}</span>
                                </div>
                                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                    <span style={{ color: '#64748b' }}>ドキュメントハッシュ</span>
                                    <span style={{ color: '#0f172a', fontWeight: '600', fontFamily: 'monospace', fontSize: '0.75rem' }}>
                                        {versionInfo.doc_hash.substring(0, 10)}...{versionInfo.doc_hash.substring(56)}
                                    </span>
                                </div>
                                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                    <span style={{ color: '#64748b' }}>署名者の役割</span>
                                    <span style={{ color: '#4f46e5', fontWeight: 'bold' }}>{role}</span>
                                </div>
                            </div>
                        </div>

                        <div style={{ marginBottom: '24px' }}>
                            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px', backgroundColor: '#fffbeb', border: '1px solid #fde68a', padding: '12px', borderRadius: '6px' }}>
                                <AlertTriangle size={18} style={{ color: '#d97706', marginTop: '2px', flexShrink: 0 }} />
                                <p style={{ fontSize: '0.75rem', color: '#92400e', margin: 0, lineHeight: 1.4 }}>
                                    署名はキャンセルできません。Metamaskで表示されるメッセージ内容が上記と一致していることを確認してください。
                                </p>
                            </div>
                        </div>

                        {error && (
                            <div style={{ backgroundColor: '#fef2f2', border: '1px solid #fee2e2', color: '#b91c1c', padding: '12px', borderRadius: '6px', marginBottom: '16px', fontSize: '0.875rem' }}>
                                {error}
                            </div>
                        )}

                        <button
                            onClick={handleSign}
                            disabled={isProcessing}
                            style={{
                                width: '100%',
                                backgroundColor: isProcessing ? '#818cf8' : '#4f46e5',
                                color: 'white',
                                fontWeight: '600',
                                padding: '14px',
                                borderRadius: '8px',
                                border: 'none',
                                cursor: isProcessing ? 'not-allowed' : 'pointer',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                gap: '8px',
                                transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
                                boxShadow: '0 4px 6px -1px rgba(79, 70, 229, 0.3)'
                            }}
                        >
                            {isProcessing ? (
                                <>
                                    <RefreshCw size={20} className="animate-spin" />
                                    署名処理中...
                                </>
                            ) : (
                                <>
                                    <PenTool size={20} />
                                    Metamaskで署名する
                                </>
                            )}
                        </button>
                    </>
                )}
            </div>
        </div>
    );

    return createPortal(modalContent, document.body);
};
