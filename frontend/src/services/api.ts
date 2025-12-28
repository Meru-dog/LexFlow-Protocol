/**
 * LexFlow Protocol - API サービス
 */
// API ベース URL
const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

// API リクエスト
async function fetchAPI<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`${API_BASE}${endpoint}`, {
        headers: {
            'Content-Type': 'application/json',
            ...options?.headers,
        },
        ...options,
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'API Error' }));
        throw new Error(error.detail || `HTTP ${response.status}`);
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

        const response = await fetch(`${API_BASE}/contracts/upload`, {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            throw new Error('Failed to upload contract');
        }

        return response.json();
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
};
