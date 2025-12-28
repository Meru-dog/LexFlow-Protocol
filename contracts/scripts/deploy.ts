import { ethers } from "hardhat";

// デプロイファンクション
async function main() {
    // インスタンスを取得
    const [deployer] = await ethers.getSigners();
    // アドレスと残高を表示
    console.log("Deploying contracts with account:", deployer.address);
    console.log("Account balance:", (await ethers.provider.getBalance(deployer.address)).toString());

    // JPYCトークンのデプロイ
    console.log("\n--- Deploying MockJPYC ---");
    // コントラクトファクトリーを取得
    const MockJPYC = await ethers.getContractFactory("MockJPYC");
    // コントラクトをデプロイ
    const mockJPYC = await MockJPYC.deploy();
    // デプロイを待つ
    await mockJPYC.waitForDeployment();
    // アドレスを取得
    const jpycAddress = await mockJPYC.getAddress();
    console.log("MockJPYC deployed to:", jpycAddress);

    // LexFlowEscrowのデプロイ
    console.log("\n--- Deploying LexFlowEscrow ---");
    // コントラクトファクトリーを取得
    const LexFlowEscrow = await ethers.getContractFactory("LexFlowEscrow");
    // コントラクトをデプロイ
    const escrow = await LexFlowEscrow.deploy(jpycAddress);
    // デプロイを待つ
    await escrow.waitForDeployment();
    // アドレスを取得
    const escrowAddress = await escrow.getAddress();
    console.log("LexFlowEscrow deployed to:", escrowAddress);

    // デプロイ要約
    console.log("\n=== Deployment Summary ===");
    console.log("MockJPYC:", jpycAddress);
    console.log("LexFlowEscrow:", escrowAddress);
    console.log("==========================\n");
    // デプロイアドレスを返す
    return { jpycAddress, escrowAddress };
}

// メインファンクションを実行
main()
    // デプロイ完了
    .then(() => process.exit(0))
    // エラー
    .catch((error) => {
        console.error(error);
        process.exit(1);
    });
