// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title ILexFlowEscrow
 * @dev 条件ベースのJPYC自動支払い用エスクローコントラクトインターフェース
 */
interface ILexFlowEscrow {
    // 各条件が今どの状態かを管理するためのフラグ
    enum ConditionStatus {
        Pending,     // 条件が承認されるまでエビデンス待ち
        Judging,     // AIが判断中
        Approved,    // 弁護士が承認
        Executed,    // 支払い実行済み
        Rejected     // 却下
    }

    // 条件の構造体
    struct Condition {
        bytes32 conditionId; // 条件の一意識別子
        address payee; // 条件達成時に支払いを受けるアドレス
        uint256 amount; // 条件承認時に支払う金額
        ConditionStatus status; // 条件の状態
        bytes32 evidenceHash; // エビデンスのハッシュ値
        uint256 createdAt; // 条件作成時刻
        uint256 executedAt; // 条件実行時刻
    }

    // 契約の構造体
    struct Contract {
        bytes32 contractId; // 契約の一意識別子
        address payer; // 支払者アドレス
        address lawyer; // 弁護士アドレス
        uint256 totalAmount; // エスクローに積まれた合計金額
        uint256 releasedAmount; // 支払済み金額
        bool isActive; // 有効フラグ
        uint256 conditionCount; // 条件数
    }

    // イベント
    event ContractCreated(bytes32 indexed contractId, address indexed payer, address lawyer, uint256 totalAmount); // 契約作成
    event ConditionAdded(bytes32 indexed contractId, bytes32 indexed conditionId, address payee, uint256 amount); // 条件追加
    event EvidenceSubmitted(bytes32 indexed contractId, bytes32 indexed conditionId, bytes32 evidenceHash); // エビデンス提出
    event ConditionApproved(bytes32 indexed contractId, bytes32 indexed conditionId); // 条件承認
    event PaymentExecuted(bytes32 indexed contractId, bytes32 indexed conditionId, address payee, uint256 amount); // 支払い実行
    event ConditionRejected(bytes32 indexed contractId, bytes32 indexed conditionId); // 条件却下

    // 外部関数
    function createContract(bytes32 contractId, address lawyer, uint256 amount) external; // 契約作成
    function addCondition(bytes32 contractId, bytes32 conditionId, address payee, uint256 amount) external; // 条件追加
    function submitEvidence(bytes32 contractId, bytes32 conditionId, bytes32 evidenceHash) external; // エビデンス提出
    function approveCondition(bytes32 contractId, bytes32 conditionId) external; // 条件承認
    function rejectCondition(bytes32 contractId, bytes32 conditionId) external; // 条件却下
    function getContract(bytes32 contractId) external view returns (Contract memory); // 契約取得
    function getCondition(bytes32 contractId, bytes32 conditionId) external view returns (Condition memory); // 条件取得
}
