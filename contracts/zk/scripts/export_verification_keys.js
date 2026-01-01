/**
 * 検証鍵のエクスポート - 全てのZK回路の検証鍵をエクスポートするスクリプト
 * 
 * このスクリプトは、コンパイルされた回路から検証鍵をエクスポートし、バックエンド検証器とチェーン上で検証するために使用します。
 */

const snarkjs = require("snarkjs");
const fs = require("fs");
const path = require("path");

const circuits = [
    { name: "kyc_verification", buildDir: "kyc" },
    { name: "conflict_of_interest", buildDir: "coi" },
    { name: "fulfillment_status", buildDir: "fulfillment" }
];

async function exportVerificationKeys() {
    console.log("📦 検証鍵のエクスポート...\n");

    let successCount = 0;
    for (const circuit of circuits) {
        const zkeyPath = path.join(__dirname, `../build/${circuit.buildDir}/${circuit.name}.zkey`);
        const vkeyPath = path.join(__dirname, `../build/${circuit.buildDir}/${circuit.name}_verification_key.json`);

        if (!fs.existsSync(zkeyPath)) {
            console.log(`⚠️   ${circuit.name}: zkeyファイルが見つかりません`);
            console.log(`   Run 'npm run setup:${circuit.buildDir === 'kyc' ? 'kyc' : circuit.buildDir === 'coi' ? 'coi' : 'fulfillment'}' first\n`);
            continue;
        }

        try {
            const vKey = await snarkjs.zKey.exportVerificationKey(zkeyPath);
            fs.writeFileSync(vkeyPath, JSON.stringify(vKey, null, 2));
            console.log(`✅ Exported: ${circuit.name}_verification_key.json`);
            successCount++;
        } catch (error) {
            console.error(`❌ Error exporting ${circuit.name}:`, error.message);
        }
    }

    if (successCount === circuits.length) {
        console.log("\n🎉 すべての検証鍵のエクスポートが正常に完了しました!");
    } else if (successCount > 0) {
        console.log(`\n⚠️  一部の検証鍵のみエクスポートされました (${successCount}/${circuits.length})`);
    } else {
        console.log("\n❌ 検証鍵はエクスポートされませんでした。セットアップを先に行ってください。");
    }
}

exportVerificationKeys().catch(console.error);
