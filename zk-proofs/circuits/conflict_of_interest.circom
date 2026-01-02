pragma circom 2.0.0;

include "../node_modules/circomlib/circuits/poseidon.circom";
include "../node_modules/circomlib/circuits/comparators.circom";

/*
 * 検証回路
 * 
 * 検証回路は、弁護士/法務事務所がクライアントとの利益衝突がないことを証明する回路で、
 * 完全なクライアントリストや関係詳細を明らかにすることなく、
 * 
 * 以下の3つの条件を証明:
 *   1. 適切な弁護士/法務事務所のクライアントリストのコミットメントを検証する
 *   2. 新しいクライアントハッシュは、弁護士/法務事務所の既存のクライアントセットに含まれていない
 *   3. 検証は正しく行われた
 */

template ConflictOfInterestCheck(maxClients) {
    // Private inputs
    signal input existingClientHashes[maxClients];  // 既存のクライアントのハッシュ
    signal input clientListSalt;                     // クライアントリストのコミットメント用の塩
    signal input firmSecret;                         // 検証用の秘密
    
    // Public inputs
    signal input newClientHash;                      // 新しいクライアントのハッシュ
    signal input expectedClientListCommitment;       // 既存のクライアントリストのコミットメント
    signal input expectedFirmHash;                   // 検証用の秘密
    
    // Output
    signal output hasNoConflict;                     // 利益相反がないことを証明する

    // Step 1: 実際のクライアントリストのコミットメントを検証する
    // Hash all client hashes together with salt
    component clientListHasher = Poseidon(maxClients + 1);
    for (var i = 0; i < maxClients; i++) {
        clientListHasher.inputs[i] <== existingClientHashes[i];
    }
    clientListHasher.inputs[maxClients] <== clientListSalt;
    
    component commitmentCheck = IsEqual();
    commitmentCheck.in[0] <== clientListHasher.out;
    commitmentCheck.in[1] <== expectedClientListCommitment;
    
    // Step 2: 新しいクライアントハッシュが既存のクライアントセットに含まれていないことを検証する
    component isNotClient[maxClients];
    signal notInList[maxClients + 1];
    notInList[0] <== 1;  // Start with true (no conflict found)
    
    for (var i = 0; i < maxClients; i++) {
        isNotClient[i] = IsEqual();
        isNotClient[i].in[0] <== existingClientHashes[i];
        isNotClient[i].in[1] <== newClientHash;
        
        // もし一致するクライアントが見つかった場合、notInListを0にする
        signal noMatchHere;
        noMatchHere <== 1 - isNotClient[i].out;
        notInList[i + 1] <== notInList[i] * noMatchHere;
    }
    
    // Step 3: 検証用の秘密を検証する
    component firmHasher = Poseidon(1);
    firmHasher.inputs[0] <== firmSecret;
    
    component firmCheck = IsEqual();
    firmCheck.in[0] <== firmHasher.out;
    firmCheck.in[1] <== expectedFirmHash;
    
    // 最終結果: 実際のクライアントリストのコミットメントが一致する AND 新しいクライアントハッシュが既存のクライアントセットに含まれていない AND 検証用の秘密が一致する
    signal intermediateResult;
    intermediateResult <== commitmentCheck.out * notInList[maxClients];
    hasNoConflict <== intermediateResult * firmCheck.out;
}

// 最大10個の既存のクライアントをサポートする
component main {public [newClientHash, expectedClientListCommitment, expectedFirmHash]} = ConflictOfInterestCheck(10);
