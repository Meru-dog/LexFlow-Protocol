pragma circom 2.0.0;

include "../node_modules/circomlib/circuits/poseidon.circom";
include "../node_modules/circomlib/circuits/comparators.circom";

/*
 * KYC 検証回路
 * 
 * ユーザーが KYC を通過したことを証明する回路で、
 * ユーザーは以下の情報を提供する:
 *   - その秘密の身分ハッシュ (プライベート)
 *   - KYC 承認のタイムスタンプ (プライベート)
 *   - 期待される KYC プロバイダーの公開鍵コミットメント (パブリック)
 * 
 * 以下の3つの条件を証明:
 *   1. ユーザーが自己の身分コミットメントのプレイントリフを知っている
 *   2. KYC は有効なプロバイダーによって承認された
 *   3. KYC は有効期間内に期限切れしていない
 */

template KYCVerification() {
    // Private inputs
    signal input identitySecret;      // ユーザーの秘密の身分値
    signal input identitySalt;        // 身分ハッシュ用のランダムなSalt
    signal input kycTimestamp;        // KYC 承認時刻
    signal input providerSecret;      // KYC プロバイダーの秘密 (コミットメント用)
    
    // Public inputs
    signal input expectedProviderHash; // 有効な KYC プロバイダーのハッシュ
    signal input currentTimestamp;     // KYC の有効期限チェック用の現在時刻
    signal input validityPeriod;       // KYC の有効期間 (秒単位)
    signal input expectedIdentityHash; // 期待されるユーザーの身分コミットメント
    
    // Output
    signal output isValid;             // KYC が有効であることを証明する

    // Step 1: 身分コミットメントを検証する
    component identityHasher = Poseidon(2);
    identityHasher.inputs[0] <== identitySecret;
    identityHasher.inputs[1] <== identitySalt;
    
    // 身分コミットメントが一致するか検証する
    component identityCheck = IsEqual();
    identityCheck.in[0] <== identityHasher.out;
    identityCheck.in[1] <== expectedIdentityHash;
    
    // Step 2: KYC プロバイダーを検証する
    component providerHasher = Poseidon(1);
    providerHasher.inputs[0] <== providerSecret;
    
    component providerCheck = IsEqual();
    providerCheck.in[0] <== providerHasher.out;
    providerCheck.in[1] <== expectedProviderHash;
    
    // Step 3: KYC が有効期間内に期限切れしていないか検証する
    signal expiryTime;
    expiryTime <== kycTimestamp + validityPeriod;
    
    component notExpired = GreaterEqThan(64);
    notExpired.in[0] <== expiryTime;
    notExpired.in[1] <== currentTimestamp;
    
    // 最終検証: 全ての検証が成功する
    signal check1;
    signal check2;
    check1 <== identityCheck.out * providerCheck.out;
    check2 <== check1 * notExpired.out;
    
    isValid <== check2;
}

component main {public [expectedProviderHash, currentTimestamp, validityPeriod, expectedIdentityHash]} = KYCVerification();
