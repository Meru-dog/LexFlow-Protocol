// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// インターフェースのインポート
import "./interfaces/IERC20.sol";  // ERC20トークン（JPYC用）インターフェース
import "./interfaces/ILexFlowEscrow.sol";  // エスクローコントラクトインターフェース

/**
 * @title LexFlowEscrow
 * @dev 条件ベースのJPYC自動支払用エスクローコントラクト
 * @notice JPYC資金を保持し、承認された条件に基づいて資金を支払うコントラクト
 * 
 * 主な機能:
 * - 契約作成時にJPYCをエスクローに預け入れ
 * - 支払条件の追加
 * - エビデンス提出（AI判定のトリガー）
 * - 弁護士による承認/却下
 * - 承認時の自動JPYC送金
 */

// ILexFlowEscrowインターフェースを継承
contract LexFlowEscrow is ILexFlowEscrow {
    // ===== 状態変数 =====
    // JPYCトークンコントラクトへの参照（不変）
    IERC20 public immutable jpycToken;
    
    // contractIdをキーに、契約全体の情報を保存
    // 契約ID => 契約データのマッピング
    mapping(bytes32 => Contract) private contracts;
    // 契約ID => (条件ID => 条件データ) のネストされたマッピング
    mapping(bytes32 => mapping(bytes32 => Condition)) private conditions;
    // 契約ID => その契約の全条件IDリスト
    mapping(bytes32 => bytes32[]) private contractConditions;

    // ===== 修飾子（Modifier） =====
    
    /**
     * @dev 支払者のみが実行できるように制限
     * @param contractId 契約ID
     */
    modifier onlyPayer(bytes32 contractId) {
        require(contracts[contractId].payer == msg.sender, "LexFlow: caller is not the payer");
        _;
    }

    /**
     * @dev 弁護士のみが実行できるように制限
     * @param contractId 契約ID
     */
    modifier onlyLawyer(bytes32 contractId) {
        require(contracts[contractId].lawyer == msg.sender, "LexFlow: caller is not the lawyer");
        _;
    }

    /**
     * @dev 契約が存在することを確認
     * @param contractId 契約ID
     */
    modifier contractExists(bytes32 contractId) {
        require(contracts[contractId].isActive, "LexFlow: contract does not exist");
        _;
    }

    /**
     * @dev 条件が存在することを確認
     * @param contractId 契約ID
     * @param conditionId 条件ID
     */
    modifier conditionExists(bytes32 contractId, bytes32 conditionId) {
        require(conditions[contractId][conditionId].conditionId == conditionId, "LexFlow: condition does not exist");
        _;
    }

    // ===== コンストラクタ =====
    
    /**
     * @dev コントラクトの初期化
     * @param _jpycToken JPYCトークンコントラクトのアドレス
     */
    constructor(address _jpycToken) {
        // JPYCアドレスの検証
        require(_jpycToken != address(0), "LexFlow: invalid JPYC address");
        jpycToken = IERC20(_jpycToken);
    }

    // ===== 外部関数 =====

    /**
     * @dev 新しい契約をエスクロー資金付きで作成
     * @param contractId 契約の一意識別子
     * @param lawyer 条件を承認できる弁護士のアドレス
     * @param amount エスクローに預ける総JPYC金額
     * 
     * 処理フロー:
     * 1. 契約が既に存在しないことを確認
     * 2. 支払者からコントラクトにJPYCを転送
     * 3. 契約データを保存
     * 4. ContractCreatedイベントを発行
     */
    function createContract(
        bytes32 contractId,
        address lawyer,
        uint256 amount
    ) external override {
        // 契約が既に存在しないことを確認
        require(contracts[contractId].contractId == bytes32(0), "LexFlow: contract already exists");
        // 弁護士アドレスの検証
        require(lawyer != address(0), "LexFlow: invalid lawyer address");
        // 金額が0より大きいことを確認
        require(amount > 0, "LexFlow: amount must be greater than 0");

        // 支払者からこのコントラクトにJPYCを転送
        // 事前にapprove()が必要
        require(
            jpycToken.transferFrom(msg.sender, address(this), amount),
            "LexFlow: JPYC transfer failed"
        );

        // 契約データを保存
        contracts[contractId] = Contract({
            contractId: contractId,           // 契約ID
            payer: msg.sender,                // 支払者アドレス
            lawyer: lawyer,                   // 弁護士アドレス
            totalAmount: amount,              // 総エスクロー金額
            releasedAmount: 0,                // リリース済み金額（初期値0）
            isActive: true,                   // 有効フラグ
            conditionCount: 0                 // 条件数（初期値0）
        });

        // イベント発行
        emit ContractCreated(contractId, msg.sender, lawyer, amount);
    }

    /**
     * @dev 既存の契約に支払条件を追加
     * @param contractId 条件を追加する契約
     * @param conditionId 条件の一意識別子
     * @param payee 条件達成時に支払いを受けるアドレス
     * @param amount 条件承認時に支払うJPYC金額
     * 
     * 支払者のみが条件を追加可能
     */
    function addCondition(
        bytes32 contractId,
        bytes32 conditionId,
        address payee,
        uint256 amount
    ) external override contractExists(contractId) onlyPayer(contractId) {
        // 条件が既に存在しないことを確認
        require(conditions[contractId][conditionId].conditionId == bytes32(0), "LexFlow: condition already exists");
        // 受取人アドレスの検証
        require(payee != address(0), "LexFlow: invalid payee address");
        // 金額が0より大きいことを確認
        require(amount > 0, "LexFlow: amount must be greater than 0");
        
        // エスクロー残高が十分かチェック
        Contract storage c = contracts[contractId];
        require(c.releasedAmount + amount <= c.totalAmount, "LexFlow: insufficient escrow balance");

        // 条件データを保存
        conditions[contractId][conditionId] = Condition({
            conditionId: conditionId,         // 条件ID
            payee: payee,                     // 受取人アドレス
            amount: amount,                   // 支払金額
            status: ConditionStatus.Pending,  // 初期状態は「保留中」
            evidenceHash: bytes32(0),         // エビデンスハッシュ（未提出）
            createdAt: block.timestamp,       // 作成日時
            executedAt: 0                     // 実行日時（未実行）
        });

        // 条件IDリストに追加
        contractConditions[contractId].push(conditionId);
        // 条件カウントを増加
        c.conditionCount++;

        // イベント発行
        emit ConditionAdded(contractId, conditionId, payee, amount);
    }

    /**
     * @dev 条件に対するエビデンスを提出（AI判定をトリガー）
     * @param contractId 条件を含む契約
     * @param conditionId エビデンスを提出する条件
     * @param evidenceHash エビデンスデータのIPFSハッシュまたはkeccak256
     * 
     * 提出者は誰でも可能（通常は条件の達成者）
     */
    function submitEvidence(
        bytes32 contractId,
        bytes32 conditionId,
        bytes32 evidenceHash
    ) external override 
      contractExists(contractId) 
      conditionExists(contractId, conditionId) 
    {
        Condition storage cond = conditions[contractId][conditionId];
        // 条件が「保留中」状態であることを確認
        require(cond.status == ConditionStatus.Pending, "LexFlow: condition not pending");

        // エビデンスハッシュを保存
        cond.evidenceHash = evidenceHash;
        // 状態を「判定中」に変更
        cond.status = ConditionStatus.Judging;

        // イベント発行
        emit EvidenceSubmitted(contractId, conditionId, evidenceHash);
    }

    /**
     * @dev 条件を承認して支払いを実行（弁護士のみ）
     * @param contractId 条件を含む契約
     * @param conditionId 承認する条件
     * 
     * 処理フロー:
     * 1. 弁護士権限の確認
     * 2. 条件の状態確認
     * 3. 承認イベント発行
     * 4. 支払実行
     */
    function approveCondition(
        bytes32 contractId,
        bytes32 conditionId
    ) external override 
      contractExists(contractId) 
      conditionExists(contractId, conditionId) 
      onlyLawyer(contractId) 
    {
        Condition storage cond = conditions[contractId][conditionId];
        // 承認可能な状態かチェック（判定中または保留中）
        require(
            cond.status == ConditionStatus.Judging || cond.status == ConditionStatus.Pending,
            "LexFlow: condition cannot be approved"
        );

        // 状態を「承認済み」に変更
        cond.status = ConditionStatus.Approved;
        // 承認イベント発行
        emit ConditionApproved(contractId, conditionId);

        // 支払いを実行
        _executePayment(contractId, conditionId);
    }

    /**
     * @dev 条件を却下（弁護士のみ）
     * @param contractId 条件を含む契約
     * @param conditionId 却下する条件
     */
    function rejectCondition(
        bytes32 contractId,
        bytes32 conditionId
    ) external override 
      contractExists(contractId) 
      conditionExists(contractId, conditionId) 
      onlyLawyer(contractId) 
    {
        Condition storage cond = conditions[contractId][conditionId];
        // 却下可能な状態かチェック
        require(
            cond.status == ConditionStatus.Judging || cond.status == ConditionStatus.Pending,
            "LexFlow: condition cannot be rejected"
        );

        // 状態を「却下」に変更
        cond.status = ConditionStatus.Rejected;
        // 却下イベント発行
        emit ConditionRejected(contractId, conditionId);
    }

    // ===== 内部関数 =====

    /**
     * @dev JPYC支払いを実行する内部関数
     * @param contractId 契約ID
     * @param conditionId 条件ID
     */
    function _executePayment(bytes32 contractId, bytes32 conditionId) internal {
        Condition storage cond = conditions[contractId][conditionId];
        Contract storage c = contracts[contractId];

        // 承認済み状態の確認
        require(cond.status == ConditionStatus.Approved, "LexFlow: condition not approved");
        // 状態を「実行済み」に更新
        cond.status = ConditionStatus.Executed;
        // 実行日時を記録
        cond.executedAt = block.timestamp;
        // リリース済み金額を加算
        c.releasedAmount += cond.amount;

        // JPYCを受取人に転送
        require(
            jpycToken.transfer(cond.payee, cond.amount),
            "LexFlow: payment transfer failed"
        );

        // 支払い実行イベント発行
        emit PaymentExecuted(contractId, conditionId, cond.payee, cond.amount);
    }

    // ===== ビュー関数（状態を変更しない読み取り専用） =====

    /**
     * @dev 契約の詳細を取得
     * @param contractId 契約ID
     * @return Contract 契約データ
     */
    function getContract(bytes32 contractId) external view override returns (Contract memory) {
        return contracts[contractId];
    }

    /**
     * @dev 条件の詳細を取得
     * @param contractId 契約ID
     * @param conditionId 条件ID
     * @return Condition 条件データ
     */
    function getCondition(
        bytes32 contractId,
        bytes32 conditionId
    ) external view override returns (Condition memory) {
        return conditions[contractId][conditionId];
    }

    /**
     * @dev 契約に属する全条件IDを取得
     * @param contractId 契約ID
     * @return bytes32[] 条件IDの配列
     */
    function getContractConditions(bytes32 contractId) external view returns (bytes32[] memory) {
        return contractConditions[contractId];
    }

    /**
     * @dev 契約のエスクロー残高を取得
     * @param contractId 契約ID
     * @return uint256 残高（総額 - 支払済み金額）
     */
    function getEscrowBalance(bytes32 contractId) external view returns (uint256) {
        Contract memory c = contracts[contractId];
        return c.totalAmount - c.releasedAmount;
    }
}
