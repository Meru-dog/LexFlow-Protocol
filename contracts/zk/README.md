# LexFlow ZK Proofs

ゼロ知識証明（Zero-Knowledge Proofs）を使用したプライバシー保護機能の実装。

## 概要

このモジュールは、LexFlow Protocolにおける以下の機能をZK証明で実現します：

| 回路 | 用途 | 証明内容 |
|------|------|----------|
| `kyc_verification` | KYC検証 | 身元情報を開示せず、KYC通過済みであることを証明 |
| `conflict_of_interest` | 利益相反チェック | クライアントリストを開示せず、新規クライアントとの利益相反がないことを証明 |
| `fulfillment_status` | 履行状態証明 | 証拠の詳細を開示せず、義務が適切に履行されたことを証明 |

## 前提条件

### 1. Circomのインストール

```bash
# Rustがインストールされていない場合
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Circomのインストール
git clone https://github.com/iden3/circom.git
cd circom
cargo build --release
cargo install --path circom

# インストール確認
circom --version
```

### 2. Powers of Tau（信頼セットアップ）のダウンロード

```bash
cd contracts/zk
curl -L https://hermez.s3-eu-west-1.amazonaws.com/powersOfTau28_hez_final_10.ptau -o powersOfTau28_hez_final_10.ptau
```

## セットアップ

```bash
cd contracts/zk
npm install
```

## 回路のコンパイル

```bash
# 全回路をコンパイル
npm run compile:all

# 個別にコンパイル
npm run compile:kyc
npm run compile:coi
npm run compile:fulfillment
```

## 信頼セットアップ（Trusted Setup）

```bash
# 各回路のzkeyを生成
npm run setup:kyc
npm run setup:coi
npm run setup:fulfillment

# 検証キーをエクスポート
npm run export:all
```

## 使用方法

### フロントエンド（ブラウザ）での証明生成

```javascript
import * as snarkjs from "snarkjs";

async function proveKYC(userInputs) {
    const { proof, publicSignals } = await snarkjs.groth16.fullProve(
        userInputs,
        "/circuits/kyc_verification.wasm",
        "/circuits/kyc_verification.zkey"
    );
    return { proof, publicSignals };
}
```

### バックエンドでの証明検証

```python
# Python (FastAPI)
from app.services.zk_verifier import verify_proof

@router.post("/verify-kyc")
async def verify_kyc(proof_data: ProofData):
    is_valid = await verify_proof(
        proof=proof_data.proof,
        public_signals=proof_data.publicSignals,
        verification_key_path="contracts/zk/build/kyc/kyc_verification_key.json"
    )
    return {"valid": is_valid}
```

## 環境変数

ZKモジュールは現在のアプリに影響を与えません。
将来的に統合する際は以下の環境変数を設定します：

```env
# .env (未使用、将来の統合用)
ZK_ENABLED=false
ZK_CIRCUITS_PATH=/path/to/contracts/zk/build
```

## ディレクトリ構造

```
contracts/zk/
├── circuits/               # Circom回路ファイル
│   ├── kyc_verification.circom
│   ├── conflict_of_interest.circom
│   └── fulfillment_status.circom
├── scripts/                # ヘルパースクリプト
│   ├── export_verification_keys.js
│   └── generate_proof.js
├── build/                  # コンパイル済みファイル（gitignore）
│   ├── kyc/
│   ├── coi/
│   └── fulfillment/
├── tests/                  # テストファイル
├── package.json
└── README.md
```

## セキュリティ上の注意

- **信頼セットアップ**: 本番環境では、MPC（Multi-Party Computation）による信頼セットアップを推奨
- **回路の監査**: デプロイ前に専門家による回路監査を推奨
- **秘密鍵管理**: ユーザーの秘密入力はブラウザ内でのみ処理し、サーバーには送信しない
