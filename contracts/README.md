# LexFlow Protocol Smart Contracts

Solidityスマートコントラクト（Hardhat）

## セットアップ

```bash
npm install
```

## コンパイル

```bash
npm run compile
```

## テスト

```bash
npm run test
```

## デプロイ

### ローカル（Hardhat Network）
```bash
npm run deploy:local
```

### Sepolia Testnet
```bash
npm run deploy:sepolia
```

## 環境変数

`.env.example` を `.env` にコピーして設定:

```
SEPOLIA_RPC_URL=https://sepolia.infura.io/v3/YOUR_KEY
PRIVATE_KEY=your_wallet_private_key
ETHERSCAN_API_KEY=your_etherscan_api_key
```

## コントラクト構成

- **LexFlowEscrow.sol**: メインエスクローコントラクト
- **MockJPYC.sol**: テスト用JPYCトークン
- **interfaces/**: インターフェース定義
