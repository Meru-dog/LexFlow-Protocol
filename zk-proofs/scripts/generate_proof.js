/**
 * 証明生成 - クライアントサイドで証明を生成するための例示スクリプト
 * 
 * このスクリプトは、各回路のZK証明を生成する方法を示します。
 * 生産環境では、snarkjsを使用してブラウザで実行します。
 */

const snarkjs = require("snarkjs");
const path = require("path");

async function generateKYCProof(inputs) {
    const wasmPath = path.join(__dirname, "../build/kyc/kyc_verification_js/kyc_verification.wasm");
    const zkeyPath = path.join(__dirname, "../build/kyc/kyc_verification.zkey");

    const { proof, publicSignals } = await snarkjs.groth16.fullProve(inputs, wasmPath, zkeyPath);
    return { proof, publicSignals };
}

async function generateCOIProof(inputs) {
    const wasmPath = path.join(__dirname, "../build/coi/conflict_of_interest_js/conflict_of_interest.wasm");
    const zkeyPath = path.join(__dirname, "../build/coi/conflict_of_interest.zkey");

    const { proof, publicSignals } = await snarkjs.groth16.fullProve(inputs, wasmPath, zkeyPath);
    return { proof, publicSignals };
}

async function generateFulfillmentProof(inputs) {
    const wasmPath = path.join(__dirname, "../build/fulfillment/fulfillment_status_js/fulfillment_status.wasm");
    const zkeyPath = path.join(__dirname, "../build/fulfillment/fulfillment_status.zkey");

    const { proof, publicSignals } = await snarkjs.groth16.fullProve(inputs, wasmPath, zkeyPath);
    return { proof, publicSignals };
}

// 他のモジュールで使用するためのExport
module.exports = {
    generateKYCProof,
    generateCOIProof,
    generateFulfillmentProof
};

// テスト用の使用例
if (require.main === module) {
    console.log("🔐 ZK Proof Generator");
    console.log("Import this module to generate proofs:");
    console.log("  const { generateKYCProof } = require('./generate_proof');");
    console.log("  const result = await generateKYCProof(inputs);");
}
