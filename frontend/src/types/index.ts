/**
 * LexFlow Protocol - API Types
 */

export type ContractStatus = 'pending' | 'active' | 'completed';
export type ConditionStatus = 'pending' | 'judging' | 'approved' | 'executed' | 'rejected';

export interface Contract {
    id: string;
    title: string;
    file_url: string;
    payer_address: string;
    lawyer_address: string;
    total_amount: number;
    released_amount: number;
    status: ContractStatus;
    blockchain_tx_hash: string | null;
    created_at: string;
    condition_count: number;
    workspace_id: string | null;
    parties: string | null;
    summary: string | null;
}

export interface ContractWithDetails extends Contract {
    conditions: Condition[];
    parsed_data: ParsedContract | null;
}

export interface Condition {
    id: string;
    contract_id: string;
    condition_type: string;
    description: string;
    payment_amount: number;
    recipient_address: string;
    status: ConditionStatus;
    created_at: string;
    executed_at: string | null;
}

export interface ParsedClause {
    clause_id: string;
    clause_type: string;
    description: string;
    amount: number | null;
    deadline: string | null;
    parties: string[];
}

export interface ParsedContract {
    contract_id: string;
    title: string;
    parties: string[];
    clauses: ParsedClause[];
    total_value: number;
    summary: string;
}

export interface Judgment {
    condition_id: string;
    ai_result: 'approved' | 'rejected';
    ai_reason: string;
    ai_confidence: number;
    judged_at: string;
}

export interface Transaction {
    id: string;
    condition_id: string;
    tx_hash: string;
    amount: number;
    from_address: string;
    to_address: string;
    block_number: number | null;
    executed_at: string;
}

export interface BlockchainStatus {
    connected: boolean;
    chain_id: number | null;
    escrow_address: string;
    jpyc_address: string;
}

// ===== Version 2: F2 義務カレンダー用の型定義 =====

export type ObligationType =
    | 'payment'           // 支払義務
    | 'renewal'           // 更新義務
    | 'termination'       // 解除義務
    | 'inspection'        // 検収義務
    | 'delivery'          // 納品義務
    | 'report'            // 報告義務
    | 'confidentiality'   // 秘密保持義務
    | 'other';            // その他

export type PartyType =
    | 'client'            // 依頼者
    | 'lawyer'            // 弁護士
    | 'counterparty'      // 相手方
    | 'both'              // 双方
    | 'unknown';          // 不明

export type RiskLevel = 'high' | 'medium' | 'low';

export type ObligationStatus =
    | 'pending'           // 保留中
    | 'due_soon'          // 期限間近（7日前）
    | 'completed'         // 完了
    | 'overdue'           // 期限超過
    | 'disputed';         // 係争中

export interface Obligation {
    id: string;
    contract_id: string;
    title: string;
    type: ObligationType;
    due_date: string | null;
    trigger_condition: string | null;
    responsible_party: PartyType;
    action: string;
    evidence_required: string[];
    risk_level: RiskLevel;
    confidence: number | null;
    clause_reference: string | null;
    status: ObligationStatus;
    completed_at: string | null;
    completed_by: string | null;
    notes: string | null;
    created_at: string;
    updated_at: string | null;
}

export interface ObligationEditHistory {
    id: string;
    obligation_id: string;
    edited_by: string;
    field_name: string;
    old_value: string | null;
    new_value: string | null;
    edited_at: string;
}

export interface ObligationCreateRequest {
    contract_id: string;
    title: string;
    type: ObligationType;
    due_date: string | null;
    trigger_condition: string | null;
    responsible_party: PartyType;
    action: string;
    evidence_required: string[];
    risk_level: RiskLevel;
    confidence: number | null;
    clause_reference: string | null;
    notes: string | null;
}

export interface ObligationUpdateRequest {
    title?: string;
    type?: ObligationType;
    due_date?: string | null;
    trigger_condition?: string | null;
    responsible_party?: PartyType;
    action?: string;
    evidence_required?: string[];
    risk_level?: RiskLevel;
    confidence?: number | null;
    clause_reference?: string | null;
    notes?: string | null;
    status?: ObligationStatus;
    edited_by: string;
}
