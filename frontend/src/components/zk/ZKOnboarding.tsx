import React, { useState, useEffect } from 'react';
import { Shield, CheckCircle, Loader2, ArrowRight, Lock, Users, FileCheck, EyeOff } from 'lucide-react';
// @ts-ignore
import * as snarkjs from 'snarkjs';
import './ZKOnboarding.css';

interface ZKOnboardingProps {
    onSuccess?: () => void;
}

type TabMode = 'kyc' | 'coi' | 'fulfillment';

const ZKOnboarding: React.FC<ZKOnboardingProps> = ({ onSuccess }) => {
    const [activeTab, setActiveTab] = useState<TabMode>('kyc');
    const [step, setStep] = useState<'intro' | 'input' | 'proving' | 'success'>('intro');

    const [kycSecret, setKycSecret] = useState('');
    const [coiList, setCoiList] = useState('');
    const [coiTarget, setCoiTarget] = useState('');
    const [fulfillmentDoc, setFulfillmentDoc] = useState('');

    const [isProcessing, setIsProcessing] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Dynamic import for circomlibjs (Poseidon)
    // @ts-ignore
    const [poseidon, setPoseidon] = useState<any>(null);
    useEffect(() => {
        const loadPoseidon = async () => {
            try {
                // @ts-ignore
                const circomlib = await import('circomlibjs');
                const p = await circomlib.buildPoseidon();
                setPoseidon(() => p);
            } catch (e) {
                console.warn("Poseidon がロードできませんでした、不正な入力により証明生成が失敗する可能性があります", e);
            }
        };
        loadPoseidon();
    }, []);

    const resetFlow = (mode: TabMode) => {
        setActiveTab(mode);
        setStep('intro');
        setKycSecret('');
        setCoiList('');
        setCoiTarget('');
        setFulfillmentDoc('');
        setError(null);
    };

    const handleStart = () => {
        setStep('input');
    };

    const hashBigInt = (inputs: (string | number | bigint)[]) => {
        if (!poseidon) return "0";
        const hash = poseidon(inputs);
        // @ts-ignore
        const hashStr = poseidon.F.toString(hash);
        return hashStr;
    }

    // Browser-compatible simple text to hex hash (simplification for demo inputs)
    const textToBigInt = (text: string) => {
        let result = "";
        for (let i = 0; i < text.length; i++) {
            result += text.charCodeAt(i).toString(16);
        }
        // 長すぎる場合は短くする
        if (result.length > 60) result = result.slice(0, 60);
        return BigInt('0x' + (result || "0"));
    }

    const generateAndVerifyProof = async () => {
        setIsProcessing(true);
        setError(null);
        setStep('proving');

        try {
            console.log(`Generating ZK Proof for ${activeTab}...`);
            const timestamp = Math.floor(Date.now() / 1000);
            const validityPeriod = 31536000; // 1 year

            let input: any = {};
            let wasmPath = "";
            let zkeyPath = "";
            let verifyEndpoint = "";
            let apiPayload: any = {};

            if (activeTab === 'kyc') {
                wasmPath = "/circuits/kyc/kyc_verification.wasm";
                zkeyPath = "/circuits/kyc/kyc_verification.zkey";
                verifyEndpoint = "/api/v1/zk/verify/kyc";

                // KYC証明のための入力準備
                const secret = BigInt(kycSecret || "12345");
                const salt = BigInt(123456); // Random salt
                const kycTime = timestamp - 100; // 100s ago
                const providerSecret = BigInt(999);

                // 公開ハッシュを計算する
                const expectedIdentityHash = hashBigInt([secret, salt]);
                const expectedProviderHash = hashBigInt([providerSecret]);

                input = {
                    identitySecret: secret.toString(),
                    identitySalt: salt.toString(),
                    kycTimestamp: kycTime,
                    providerSecret: providerSecret.toString(),
                    expectedProviderHash: expectedProviderHash,
                    currentTimestamp: timestamp,
                    validityPeriod: validityPeriod,
                    expectedIdentityHash: expectedIdentityHash
                };

                apiPayload = {
                    expected_provider_hash: expectedProviderHash,
                    current_timestamp: timestamp,
                    validity_period: validityPeriod,
                    expected_identity_hash: expectedIdentityHash
                }

            } else if (activeTab === 'coi') {
                wasmPath = "/circuits/coi/conflict_of_interest.wasm";
                zkeyPath = "/circuits/coi/conflict_of_interest.zkey";
                verifyEndpoint = "/api/v1/zk/verify/coi";

                // COI証明のための入力準備 (回路定義: maxClients=10)
                const maxClients = 10;
                const existingClientHashes = new Array(maxClients).fill("0");
                const clients = coiList.split(',').map(s => s.trim()).filter(s => s);

                // 既存のクライアントをハッシュする
                clients.forEach((client, idx) => {
                    if (idx < maxClients) {
                        existingClientHashes[idx] = hashBigInt([textToBigInt(client)]);
                    }
                });

                // 隠しパラメータ (Salt/Secret)
                const clientListSalt = BigInt(12345);
                const firmSecret = BigInt(888);
                const expectedFirmHash = hashBigInt([firmSecret]);

                // 新しいクライアントをハッシュする
                const targetInt = textToBigInt(coiTarget);
                const newClientHash = hashBigInt([targetInt]);

                // Commitmentを計算する (Poseidon(maxClients + 1))
                // 回路側のロジック: Hash(existingHashes + salt)
                const listCommitment = hashBigInt([...existingClientHashes, clientListSalt]);

                input = {
                    existingClientHashes: existingClientHashes,
                    clientListSalt: clientListSalt.toString(),
                    firmSecret: firmSecret.toString(),
                    newClientHash: newClientHash,
                    expectedClientListCommitment: listCommitment,
                    expectedFirmHash: expectedFirmHash
                };

                apiPayload = {
                    new_client_hash: newClientHash,
                    expected_client_list_commitment: listCommitment,
                    expected_firm_hash: expectedFirmHash
                }

            } else if (activeTab === 'fulfillment') {
                wasmPath = "/circuits/fulfillment/fulfillment_status.wasm";
                zkeyPath = "/circuits/fulfillment/fulfillment_status.zkey";
                verifyEndpoint = "/api/v1/zk/verify/fulfillment";

                // Fulfillment Inputs
                const secretVal = textToBigInt(fulfillmentDoc || "10000");
                const obligationSalt = BigInt(555);
                const contractId = BigInt(123);

                // Calculate obligation hash (Poseidon(3): secret, salt, contractId)
                const expectedObligationHash = hashBigInt([secretVal, obligationSalt, contractId]);

                // Evidence
                const evidenceData = BigInt(999); // Mock evidence hash
                const evidenceSalt = BigInt(777);
                const expectedEvidenceType = hashBigInt([evidenceData, evidenceSalt]);

                // Fulfiller
                const fulfillerSecret = BigInt(111);
                const expectedFulfillerHash = hashBigInt([fulfillerSecret]);

                const deadline = timestamp + 86400; // +1 day
                const fulfillmentTime = timestamp - 3600; // 1 hour ago (valid)

                input = {
                    obligationSecret: secretVal.toString(),
                    obligationSalt: obligationSalt.toString(),
                    evidenceData: evidenceData.toString(),
                    evidenceSalt: evidenceSalt.toString(),
                    fulfillerSecret: fulfillerSecret.toString(),
                    fulfillmentTimestamp: fulfillmentTime,
                    expectedObligationHash: expectedObligationHash,
                    expectedEvidenceType: expectedEvidenceType,
                    expectedFulfillerHash: expectedFulfillerHash,
                    deadlineTimestamp: deadline,
                    contractId: contractId.toString()
                };

                apiPayload = {
                    expected_obligation_hash: expectedObligationHash,
                    expected_evidence_type: expectedEvidenceType,
                    expected_fulfiller_hash: expectedFulfillerHash,
                    deadline_timestamp: deadline,
                    contract_id: contractId.toString()
                }
            }

            // 1. ZK証明を生成する
            const { proof, publicSignals } = await snarkjs.groth16.fullProve(input, wasmPath, zkeyPath);

            console.log("Proof Generated:", proof);
            console.log("Public Signals:", publicSignals);

            // 2. ZK証明をバックエンドで検証する
            const payload = {
                proof: {
                    pi_a: proof.pi_a.slice(0, 3),
                    pi_b: proof.pi_b.slice(0, 3),
                    pi_c: proof.pi_c.slice(0, 3),
                    protocol: proof.protocol,
                    curve: proof.curve
                },
                public_signals: publicSignals,
                ...apiPayload
            };

            const response = await fetch(verifyEndpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            const data = await response.json();

            if (!response.ok || !data.valid) {
                throw new Error(data.message || 'Back-end verification failed');
            }

            // 3. 数学的な結果をチェック (publicSignals[0] が 1 なら成功)
            if (publicSignals[0] !== '1') {
                if (activeTab === 'coi') {
                    throw new Error('利益相反(Conflict)が検出されました。この案件を受任することはできません。');
                } else if (activeTab === 'fulfillment') {
                    throw new Error('履行条件を満たしていません。');
                } else {
                    throw new Error('検証条件を満たしていません。');
                }
            }

            setStep('success');
            if (onSuccess && activeTab === 'kyc') onSuccess();

        } catch (err: any) {
            console.error(err);
            setError('Verification Failed: ' + (err.message || 'Unknown error'));
            setStep('input');
        } finally {
            setIsProcessing(false);
        }
    };

    const getTabConfig = () => {
        switch (activeTab) {
            case 'kyc':
                return {
                    title: "プライバシー保護KYC",
                    icon: <Shield className="zk-icon" size={48} />,
                    desc: "あなたの個人情報をサーバーに送信することなく、認証機関が発行した『正当性』のみを数学的に証明します。",
                    inputTitle: "秘密鍵の入力",
                    inputDesc: "認証機関から発行された秘密鍵(Identity Secret)を入力してください。この値はデバイス外に出ません。"
                };
            case 'coi':
                return {
                    title: "利益相反(COI)チェック",
                    icon: <Users className="zk-icon" size={48} />,
                    desc: "あなたの『顧客リスト』をサーバーに渡すことなく、今回の案件の『相手方（相手方代理人など）』が既存顧客と衝突していないかを証明します。",
                    inputTitle: "ローカル照合データの入力",
                    inputDesc: "守秘義務のある顧客リストと、今回の案件で対立する『相手方名』を入力してください。照合はブラウザ内で完結します。"
                };
            case 'fulfillment':
                return {
                    title: "機密情報の履行証明",
                    icon: <FileCheck className="zk-icon" size={48} />,
                    desc: "JPYCでの送金（支払い）以外の「義務」—例えば、物理的な商品の引き渡しや、秘密保持下でのデータ提供など—が完了したことを、内容を明かさずに証明します。",
                    inputTitle: "履行証拠の入力",
                    inputDesc: "証明の根拠となる機密データ（署名済みの受領書ハッシュ、配送伝票番号、または達成したKPI数値）を入力してください。"
                };
        }
    };

    const config = getTabConfig();

    return (
        <div className="zk-onboarding-container">
            {/* Tab Navigation */}
            <div className="zk-tabs">
                <button
                    className={`zk-tab ${activeTab === 'kyc' ? 'active' : ''}`}
                    onClick={() => resetFlow('kyc')}
                >
                    <Shield size={16} /> KYC証明
                </button>
                <button
                    className={`zk-tab ${activeTab === 'coi' ? 'active' : ''}`}
                    onClick={() => resetFlow('coi')}
                >
                    <Users size={16} /> 利益相反
                </button>
                <button
                    className={`zk-tab ${activeTab === 'fulfillment' ? 'active' : ''}`}
                    onClick={() => resetFlow('fulfillment')}
                >
                    <FileCheck size={16} /> 履行証明
                </button>
            </div>

            <div className="zk-card">
                {step === 'intro' && (
                    <div className="zk-content fade-in">
                        <div className="zk-icon-wrapper pulse">
                            {config.icon}
                        </div>
                        <h2>{config.title}</h2>
                        <p>{config.desc}</p>

                        <div className="zk-features">
                            <div className="zk-feature">
                                <Lock size={18} />
                                <span>情報はデバイス内で完結</span>
                            </div>
                            <div className="zk-feature">
                                <EyeOff size={18} />
                                <span>サーバーへの秘密開示なし</span>
                            </div>
                        </div>

                        <button className="zk-btn zk-btn-primary" onClick={handleStart}>
                            検証プロセスを開始 <ArrowRight size={18} />
                        </button>
                    </div>
                )}

                {step === 'input' && (
                    <div className="zk-content fade-in">
                        <div className="zk-header">
                            <button className="zk-back" onClick={() => setStep('intro')}>戻る</button>
                            <h3>{config.inputTitle}</h3>
                        </div>
                        <p className="zk-description">{config.inputDesc}</p>

                        <div className="zk-input-container">
                            {activeTab === 'kyc' && (
                                <div className="zk-input-group">
                                    <label>KYC秘密鍵 (Identity Secret)</label>
                                    <input
                                        type="password"
                                        value={kycSecret}
                                        onChange={(e) => setKycSecret(e.target.value)}
                                        placeholder="0x..."
                                    />
                                    <p className="zk-help-text">
                                        ※提携するKYCプロバイダー（例: デジタル身分証サービス）から安全に発行された秘密鍵を想定しています。この鍵はブラウザ内でのみ使用され、サーバーに送信されることはありません。
                                    </p>
                                </div>
                            )}

                            {activeTab === 'coi' && (
                                <>
                                    <div className="zk-input-group">
                                        <label>守秘義務のある既存顧客リスト (CSV/Text)</label>
                                        <textarea
                                            value={coiList}
                                            onChange={(e) => setCoiList(e.target.value)}
                                            placeholder="Client A, Client B, Client C..."
                                            rows={3}
                                            className="zk-textarea-secret"
                                        />
                                        <small><Lock size={12} /> このリストは送信されません</small>
                                    </div>
                                    <div className="zk-input-group">
                                        <label>今回対立する『相手方（Adverse Party）』の名前</label>
                                        <input
                                            type="text"
                                            value={coiTarget}
                                            onChange={(e) => setCoiTarget(e.target.value)}
                                            placeholder="Example Corp"
                                        />
                                        <p className="zk-help-text">
                                            既存顧客を相手方として案件を受任することは原則として利益相反となります。このツールは、リスト自体を明かさずに「相手方がリストに含まれていない」ことを数学的に証明します。
                                        </p>
                                    </div>
                                </>
                            )}

                            {activeTab === 'fulfillment' && (
                                <div className="zk-input-group">
                                    <label>履行証拠データ (秘密の値/ハッシュ)</label>
                                    <input
                                        type="password"
                                        value={fulfillmentDoc}
                                        onChange={(e) => setFulfillmentDoc(e.target.value)}
                                        placeholder="Secret Evidence Data"
                                    />
                                    <small><Lock size={12} /> この生データはあなたのデバイス外に出ません。サーバーには「履行完了」の証明のみが届きます。</small>
                                </div>
                            )}
                        </div>

                        {error && <span className="zk-error-text">{error}</span>}

                        <button
                            className="zk-btn zk-btn-primary"
                            onClick={generateAndVerifyProof}
                            disabled={!poseidon || isProcessing ||
                                (activeTab === 'kyc' && !kycSecret) ||
                                (activeTab === 'coi' && (!coiList || !coiTarget)) ||
                                (activeTab === 'fulfillment' && !fulfillmentDoc)
                            }
                        >
                            {!poseidon ? "暗号化モジュールをロード中..." : (isProcessing ? "ZK証明を計算中..." : "証明を生成して検証")}
                        </button>
                    </div>
                )}

                {step === 'proving' && (
                    <div className="zk-content fade-in">
                        <div className="zk-loader-wrapper">
                            <Loader2 className="zk-spinner" size={48} />
                        </div>
                        <h3>ゼロ知識証明を生成中...</h3>
                        <p>
                            ブラウザ内(WASM)で計算を実行中。<br />
                            あなたの秘密情報は暗号化された「Proof」に変換され、<br />
                            生データは一切外部に出ません。
                        </p>
                    </div>
                )}

                {step === 'success' && (
                    <div className="zk-content fade-in">
                        <div className="zk-icon-wrapper success-pop">
                            <CheckCircle className="zk-icon success" size={48} />
                        </div>
                        <h3>検証成功 (Verified)</h3>
                        <p>
                            {activeTab === 'kyc' && "KYCの正当性が証明されました。"}
                            {activeTab === 'coi' && "利益相反がないことが証明されました。"}
                            {activeTab === 'fulfillment' && "条件の履行が証明されました。"}
                            <br />
                            サーバーには「証明書」のみが記録されます。
                        </p>
                        <button className="zk-btn zk-btn-success" onClick={() => resetFlow(activeTab)}>
                            別の証明を行う
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
};

export default ZKOnboarding;
