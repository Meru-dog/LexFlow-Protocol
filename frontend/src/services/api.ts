// API ベース URL の自動検出
// ローカル開発時: http://localhost:8000/api/v1
// デプロイ時: 環境変数で指定されたURL
const getApiBaseUrl = () => {
    // 開発環境（localhost/127.0.0.1）かどうかを確認
    const hostname = window.location.hostname;
    const isLocalhost = hostname === 'localhost' || hostname === '127.0.0.1';

    // 環境変数の取得
    const envUrl = import.meta.env.VITE_API_URL;

    // ローカルホストでの実行を最優先（.envに本番URLがあってもローカルを優先）
    if (isLocalhost) {
        return 'http://localhost:8000/api/v1';
    }

    // デプロイ環境では環境変数を使用
    if (envUrl) {
        return envUrl;
    }

    // デフォルト（フォールバック）
    return 'http://localhost:8000/api/v1';
};

const API_BASE = getApiBaseUrl();
const BASE_URL = API_BASE.replace('/api/v1', '');

console.log('🔗 API Base URL:', API_BASE);

export const getFileUrl = (path: string) => {
    if (!path) return '';
    if (path.startsWith('http')) return path;
    // 先頭のスラッシュを調整
    const normalizedPath = path.startsWith('/') ? path : `/${path}`;
    return `${BASE_URL}${normalizedPath}`;
};

// API リクエスト
async function fetchAPI<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const { headers, body, ...rest } = options || {};

    // トークンを localStorage から取得
    const token = localStorage.getItem('access_token');

    // 適切なヘッダーを構築
    const defaultHeaders: Record<string, string> = {};

    // body が FormData でない場合のみ Content-Type を設定
    if (!(body instanceof FormData)) {
        defaultHeaders['Content-Type'] = 'application/json';
    }

    if (token) {
        defaultHeaders['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_BASE}${endpoint}`, {
        headers: {
            ...defaultHeaders,
            ...headers,
        },
        body,
        ...rest,
    });

    if (!response.ok) {
        // F8: x402 Paywall Handling
        if (response.status === 402) {
            const paymentHeader = response.headers.get('PAYMENT-REQUIRED');
            if (paymentHeader) {
                const paymentInfo = JSON.parse(paymentHeader);
                const error: any = new Error('支払いが必要です');
                error.status = 402;
                error.paymentInfo = paymentInfo;
                throw error;
            }
        }

        const errorData = await response.json().catch(() => ({ detail: 'API エラー' }));
        let errorMessage = '';

        if (Array.isArray(errorData.detail)) {
            // Pydantic validation errors
            errorMessage = errorData.detail.map((err: any) => {
                const loc = err.loc ? err.loc.join('.') : '';
                return `${loc}: ${err.msg}`;
            }).join('\n');
        } else if (typeof errorData.detail === 'object') {
            errorMessage = JSON.stringify(errorData.detail);
        } else {
            errorMessage = errorData.detail || `HTTP ${response.status}`;
        }

        const error: any = new Error(errorMessage);
        error.status = response.status;
        error.detail = errorData.detail;
        throw error;
    }

    return response.json();
}

// API サービス
export const api = {
    // コントラクトアップロード
    async uploadContract(file: File, title?: string, payerAddress?: string, lawyerAddress?: string, totalAmount?: number) {
        const formData = new FormData();
        formData.append('file', file);
        if (title) formData.append('title', title);
        if (payerAddress) formData.append('payer_address', payerAddress);
        if (lawyerAddress) formData.append('lawyer_address', lawyerAddress);
        if (totalAmount) formData.append('total_amount', totalAmount.toString());

        return fetchAPI<any>('/contracts/upload', {
            method: 'POST',
            body: formData,
        });
    },

    // コントラクト取得
    async getContracts(status?: string) {
        const params = status ? `?status=${status}` : '';
        return fetchAPI(`/contracts${params}`);
    },

    // コントラクト取得
    async getContract(id: string) {
        return fetchAPI(`/contracts/${id}`);
    },

    // 契約書全文テキストを取得
    async getContractText(id: string): Promise<{ text: string }> {
        return fetchAPI(`/contracts/${id}/text`);
    },

    // コントラクトアクティベーション
    async activateContract(id: string) {
        return fetchAPI(`/contracts/${id}/activate`, { method: 'POST' });
    },

    // 条項追加
    async addCondition(contractId: string, condition: {
        condition_type: string;
        description: string;
        payment_amount: number;
        recipient_address: string;
    }) {
        return fetchAPI(`/contracts/${contractId}/conditions`, {
            method: 'POST',
            body: JSON.stringify(condition),
        });
    },

    // 判決提出
    async submitEvidence(conditionId: string, evidence: {
        evidence_text?: string;
        evidence_url?: string;
    }) {
        return fetchAPI(`/judgments/conditions/${conditionId}/evidence`, {
            method: 'POST',
            body: JSON.stringify(evidence),
        });
    },

    // 判決取得
    async getJudgment(conditionId: string) {
        return fetchAPI(`/judgments/conditions/${conditionId}`);
    },

    // 条項承認
    async approveCondition(conditionId: string, approval: {
        result: 'approved' | 'rejected';
        comment?: string;
    }, lawyerAddress?: string) {
        const params = lawyerAddress ? `?lawyer_address=${lawyerAddress}` : '';
        return fetchAPI(`/judgments/conditions/${conditionId}/approve${params}`, {
            method: 'POST',
            body: JSON.stringify(approval),
        });
    },

    // トランザクション取得
    async getTransaction(conditionId: string) {
        return fetchAPI(`/judgments/transactions/${conditionId}`);
    },

    // ブロックチェーン状態取得
    async getBlockchainStatus() {
        return fetchAPI('/blockchain/status');
    },

    // ===== Version 2: F2 義務カレンダーAPI =====

    // 契約書から義務を自動抽出
    async extractObligations(contractId: string, contractText?: string, paymentSignature?: string) {
        const headers: Record<string, string> = {};
        if (paymentSignature) {
            headers['PAYMENT-SIGNATURE'] = paymentSignature;
        }

        return fetchAPI('/obligations/extract', {
            method: 'POST',
            body: JSON.stringify({
                contract_id: contractId,
                contract_text: contractText || null
            }),
            headers
        });
    },

    // 特定の契約の義務を取得
    async getObligationsByContract(contractId: string) {
        return fetchAPI(`/obligations/contract/${contractId}`);
    },

    // 義務を作成
    async createObligation(data: any) {
        return fetchAPI('/obligations', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },

    // 義務を更新
    async updateObligation(obligationId: string, data: any) {
        return fetchAPI(`/obligations/${obligationId}`, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    },

    // 義務を完了状態にする
    async completeObligation(obligationId: string, completedBy: string) {
        return fetchAPI(`/obligations/${obligationId}/complete`, {
            method: 'POST',
            body: JSON.stringify({ completed_by: completedBy })
        });
    },

    // 期限間近の義務を取得
    async getDueSoonObligations() {
        return fetchAPI('/obligations/due-soon');
    },

    // 期限超過の義務を取得
    async getOverdueObligations() {
        return fetchAPI('/obligations/overdue');
    },

    // ===== Version 2: F3 オンチェーン署名・版管理API =====

    // 案件の全バージョンを取得
    async getVersionsByCase(caseId: string) {
        return fetchAPI(`/versions/case/${caseId}`);
    },

    // 新しいバージョンを作成（ファイルアップロード）
    async createVersion(caseId: string, file: File, title: string, creatorAddress: string, summary?: string) {
        const formData = new FormData();
        formData.append('case_id', caseId);
        formData.append('file', file, file.name);
        formData.append('title', title);
        formData.append('creator_address', creatorAddress);
        if (summary) formData.append('summary', summary);

        return fetchAPI<any>('/versions', {
            method: 'POST',
            body: formData,
        });
    },

    // 署名を提出
    async submitSignature(data: {
        version_id: string;
        signer: string;
        role: string;
        signature: string;
        timestamp: number;
    }) {
        return fetchAPI('/signatures', {
            method: 'POST',
            body: JSON.stringify(data),
        });
    },

    // バージョンに紐づく署名を取得
    async getSignaturesByVersion(versionId: string) {
        return fetchAPI(`/signatures/version/${versionId}`);
    },

    // システム設定（公開情報）を取得
    async getConfig(): Promise<{ chainId: number, escrowAddress: string, jpycAddress?: string, appName?: string }> {
        return fetchAPI('/config');
    },

    // ===== F4: Redline比較API =====

    // 2つのバージョンを比較
    async compareVersions(oldVersionId: string, newVersionId: string) {
        return fetchAPI('/redline/compare', {
            method: 'POST',
            body: JSON.stringify({
                old_version_id: oldVersionId,
                new_version_id: newVersionId
            }),
        });
    },

    // 比較可能なバージョン一覧を取得
    async getComparableVersions(caseId: string) {
        return fetchAPI(`/redline/versions/${caseId}`);
    },

    // ===== 監査証跡API =====
    async getAuditEvents(params?: {
        workspace_id?: string;
        contract_id?: string;
        actor_id?: string;
        event_type?: string;
        from_date?: string;
        to_date?: string;
        page?: number;
        page_size?: number;
    }) {
        const queryString = params ? '?' + new URLSearchParams(
            Object.entries(params).reduce((acc, [key, value]) => {
                if (value !== undefined && value !== null) {
                    acc[key] = String(value);
                }
                return acc;
            }, {} as Record<string, string>)
        ).toString() : '';
        return fetchAPI(`/audit/events${queryString}`);
    },

    async getAuditEventTypes() {
        return fetchAPI('/audit/types');
    },

    async verifyAuditChain(params?: { workspace_id?: string; limit?: number }) {
        const queryString = params ? '?' + new URLSearchParams(
            Object.entries(params).reduce((acc, [key, value]) => {
                if (value !== undefined && value !== null) {
                    acc[key] = String(value);
                }
                return acc;
            }, {} as Record<string, string>)
        ).toString() : '';
        return fetchAPI(`/audit/verify${queryString}`);
    },

    async exportAuditEvents(format: 'csv' | 'json', params?: {
        workspace_id?: string;
        contract_id?: string;
        actor_id?: string;
        event_type?: string;
        from_date?: string;
        to_date?: string;
        limit?: number;
    }) {
        const allParams = { format, ...params };
        const queryString = '?' + new URLSearchParams(
            Object.entries(allParams).reduce((acc, [key, value]) => {
                if (value !== undefined && value !== null) {
                    acc[key] = String(value);
                }
                return acc;
            }, {} as Record<string, string>)
        ).toString();

        const token = localStorage.getItem('access_token');
        const response = await fetch(`${API_BASE}/audit/export${queryString}`, {
            headers: {
                ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
            }
        });

        if (!response.ok) {
            throw new Error('監査証跡のエクスポートに失敗しました');
        }
        return response.blob();
    },

    // ===== プロフィールAPI =====
    async getProfile() {
        return fetchAPI('/users/me');
    },

    async updateProfile(data: { display_name?: string; slack_webhook_url?: string }) {
        return fetchAPI('/users/me', {
            method: 'PATCH',
            body: JSON.stringify(data),
        });
    },

    async testSlackNotification() {
        return fetchAPI('/users/me/test-slack', {
            method: 'POST'
        });
    },

    // ===== 通知API =====
    async getNotifications(params?: {
        status?: string;
        channel?: string;
        limit?: number;
    }) {
        const queryString = params ? '?' + new URLSearchParams(
            Object.entries(params).reduce((acc, [key, value]) => {
                if (value !== undefined && value !== null) {
                    acc[key] = String(value);
                }
                return acc;
            }, {} as Record<string, string>)
        ).toString() : '';
        return fetchAPI(`/notifications${queryString}`);
    },

    async resendNotification(notificationId: string) {
        return fetchAPI(`/notifications/${notificationId}/resend`, {
            method: 'POST',
        });
    },

    getFileUrl, // ヘルパー関数を追加
};
