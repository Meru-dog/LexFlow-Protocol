/**
 * LexFlow Protocol - API Types
 */

export type ContractStatus = 'pending' | 'active' | 'completed';
export type ConditionStatus = 'pending' | 'judging' | 'approved' | 'executed' | 'rejected';

export interface Contract {
    id: string;
    title: string;
    pdf_url: string;
    payer_address: string;
    lawyer_address: string;
    total_amount: number;
    released_amount: number;
    status: ContractStatus;
    blockchain_tx_hash: string | null;
    created_at: string;
    condition_count: number;
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
