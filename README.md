# LexFlow Protocol

**AI reads the contract, Ethereum executes it, and JPYC moves the money.**

A protocol that synchronizes contract fulfillment and execution using AI and Web3.

[日本語版ドキュメント](README.md) <!-- Since this is the main README, we can keep Japanese or switch to English. The user writes in Japanese, so I will stick to Japanese but adopt the Deployment Guide structure. -->
<!-- Wait, standard practice for public repos often involves English, but the user's prompt is Japanese and the target audience seems Japanese (Softbank award). I will keep it in Japanese but make it deployment-ready. -->

---

## 📋 概要

LexFlow Protocolは、PDF契約書の自動解析からAI判定、弁護士承認、ブロックチェーン決済までを一気通貫で実現する次世代の契約管理プラットフォームです。

**コンセプト**:  
「AIが契約を読み、Ethereumが契約を実行し、JPYCが資金を動かす。」

### 🎯 解決する課題

- **手動プロセス**: 契約書の内容確認、条件チェック、支払処理の自動化
- **不透明性**: ブロックチェーンによる承認プロセスや決済履歴の可視化
- **不払いリスク**: エスクロー（資金ロック）による確実な支払いの担保
- **紛争回避**: AIと弁護士による二重チェックと、オンチェーン証跡による事実証明

---

## 🚀 デプロイとセットアップ

このアプリケーションをご自身の環境やクラウドにデプロイして利用するためのガイドです。

### 0. 前提条件

- **GitHubアカウント**
- **OpenAI API Key** (GPT-4利用のため)
- **Infura / Alchemy Key** (Sepolia接続のため)
- **Ethereum Wallet Private Key** (Sepolia ETHが必要)

### 1. リポジトリのセットアップ

1. このリポジトリをFork、またはご自身のアカウントにPushしてください。
   - **注意**: `.env` ファイルなどの機密情報は `.gitignore` により除外されています。これらを誤ってコミットしないよう注意してください。

### 2. バックエンドのデプロイ (Render / Railway / Heroku 等)

`backend` ディレクトリをデプロイします。以下の環境変数を設定してください。

| 変数名 | 説明 | 例 |
|---|---|---|
| `OPENAI_API_KEY` | OpenAI APIキー | `sk-...` |
| `DATABASE_URL` | PostgreSQL接続URL | `postgresql+asyncpg://...` |
| `ETHEREUM_RPC_URL` | Sepolia RPCエンドポイント | `https://sepolia.infura.io/v3/...` |
| `PRIVATE_KEY` | トランザクション受信用ウォレット秘密鍵 | `0x...` |
| `ESCROW_CONTRACT_ADDRESS` | エスクローコントラクト (下記参照) | `0xbDad48381B2EAEeD4a5bfaC8c45601a7dE555B95` |
| `JPYC_CONTRACT_ADDRESS` | JPYCコントラクト (下記参照) | `0x138D4810c6D977eE490f67D9659Cb26A89d630f9` |
| `CORS_ORIGINS` | フロントエンドのURL | `https://your-frontend.vercel.app` |

### 3. フロントエンドのデプロイ (Vercel / Netlify 等)

`frontend` ディレクトリをデプロイします。

- **Framework**: Vite
- **Build Command**: `npm run build`
- **Output Directory**: `dist`

環境変数の設定:

| 変数名 | 説明 | 例 |
|---|---|---|
| `VITE_API_URL` | デプロイしたバックエンドのAPI URL | `https://your-backend.onrender.com/api/v1` |

---

## 🌐 デプロイ済みコントラクト (Sepolia Testnet)

本システムは以下のコントラクトを利用して動作します。

| コントラクト名 | アドレス | 説明 |
|---|---|---|
| **LexFlowEscrow** | `0xbDad48381B2EAEeD4a5bfaC8c45601a7dE555B95` | 契約実行と資金管理を行うコアコントラクト |
| **MockJPYC** | `0x138D4810c6D977eE490f67D9659Cb26A89d630f9` | テスト用日本円ステーブルコイン (ERC20) |

---

## 🛠 技術スタック

| レイヤー | 技術 |
|---------|------|
| **Smart Contract** | Solidity, Hardhat, OpenZeppelin |
| **Backend** | Python, FastAPI, LangGraph, OpenAI API, Web3.py |
| **Frontend** | TypeScript, React, Vite, ethers.js |
| **Infrastructure** | Ethereum (Sepolia), Render/Vercel (推奨) |

---

## 📄 ライセンス

MIT License
