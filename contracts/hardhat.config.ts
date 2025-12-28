import { HardhatUserConfig } from "hardhat/config"; // Hardhatの設定
import "@nomicfoundation/hardhat-toolbox"; // Hardhatのツールボックス
import * as dotenv from "dotenv"; // 環境変数の読み込み

dotenv.config();

// Hardhatの設定
const config: HardhatUserConfig = {
    // Solidityの設定
    solidity: {
        version: "0.8.20",
        settings: {
            optimizer: {
                enabled: true,
                runs: 200,
            },
        },
    },
    // ネットワークの設定
    networks: {
        hardhat: {
            chainId: 31337,
        },
        sepolia: {
            url: process.env.SEPOLIA_RPC_URL || "",
            accounts: process.env.PRIVATE_KEY ? [process.env.PRIVATE_KEY] : [],
        },
    },
    // Etherscanの設定
    etherscan: {
        apiKey: process.env.ETHERSCAN_API_KEY || "",
    },
    // パスの設定
    paths: {
        sources: "./contracts",
        tests: "./test",
        cache: "./cache",
        artifacts: "./artifacts",
    },
};

export default config;
