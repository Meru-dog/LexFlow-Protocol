pragma circom 2.0.0;

include "../node_modules/circomlib/circuits/poseidon.circom";
include "../node_modules/circomlib/circuits/comparators.circom";

/*
 * 契約の履行状況検証回路
 * 
 * 契約の義務を履行したことを証明する回路で、証拠や契約の詳細を明らかにすることなく、
 * 契約の義務を履行したことを証明する回路
 * 
 * 以下の4つの条件を証明:
 *   1. 契約の義務を履行したことを証明する
 *   2. 証拠のハッシュが必要な証拠タイプと一致する
 *   3. 契約の履行日時が期限日時以内である
 *   4. 実行者は許可されている
 */

template FulfillmentStatusVerification() {
    // Private inputs
    signal input obligationSecret;      // 契約の義務の秘密成分
    signal input obligationSalt;        // 契約の義務のハッシュ用のSalt
    signal input evidenceData;          // 実際の証拠のハッシュ
    signal input evidenceSalt;          // 証拠のコミットメント用のSalt
    signal input fulfillerSecret;       // 実行者の秘密成分
    signal input fulfillmentTimestamp;  // 契約の義務を履行した日時
    
    // Public inputs
    signal input expectedObligationHash;   // 契約の義務のコミットメント
    signal input expectedEvidenceType;     // 必要な証拠タイプのハッシュ
    signal input expectedFulfillerHash;    // 許可されている実行者のハッシュ
    signal input deadlineTimestamp;        // 契約の履行の期限
    signal input contractId;               // 契約の識別子 (束縛用)
    
    // Output
    signal output isFulfilled;             // 契約の義務を履行したことを証明する

    // Step 1: 契約の義務のコミットメントを検証
    component obligationHasher = Poseidon(3);
    obligationHasher.inputs[0] <== obligationSecret;
    obligationHasher.inputs[1] <== obligationSalt;
    obligationHasher.inputs[2] <== contractId;
    
    component obligationCheck = IsEqual();
    obligationCheck.in[0] <== obligationHasher.out;
    obligationCheck.in[1] <== expectedObligationHash;
    
    // Step 2: 証拠のコミットメントを検証
    component evidenceHasher = Poseidon(2);
    evidenceHasher.inputs[0] <== evidenceData;
    evidenceHasher.inputs[1] <== evidenceSalt;
    
    component evidenceCheck = IsEqual();
    evidenceCheck.in[0] <== evidenceHasher.out;
    evidenceCheck.in[1] <== expectedEvidenceType;
    
    // Step 3: 実行者のコミットメントを検証
    component fulfillerHasher = Poseidon(1);
    fulfillerHasher.inputs[0] <== fulfillerSecret;
    
    component fulfillerCheck = IsEqual();
    fulfillerCheck.in[0] <== fulfillerHasher.out;
    fulfillerCheck.in[1] <== expectedFulfillerHash;
    
    // Step 4: 契約の履行日時が期限日時以内であることを検証
    component beforeDeadline = LessEqThan(64);
    beforeDeadline.in[0] <== fulfillmentTimestamp;
    beforeDeadline.in[1] <== deadlineTimestamp;
    
    // Final validation: 全ての検証が成功する
    signal check1;
    signal check2;
    signal check3;
    
    check1 <== obligationCheck.out * evidenceCheck.out;
    check2 <== check1 * fulfillerCheck.out;
    check3 <== check2 * beforeDeadline.out;
    
    isFulfilled <== check3;
}

component main {public [expectedObligationHash, expectedEvidenceType, expectedFulfillerHash, deadlineTimestamp, contractId]} = FulfillmentStatusVerification();
