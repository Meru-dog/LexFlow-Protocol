import { ethers } from "hardhat";

/**
 * MockJPYC デプロイスクリプト
 * Sepolia テストネット用のテストJPYCトークンをデプロイします
 */
async function main() {
    console.log("🚀 Deploying MockJPYC to Sepolia...");

    const [deployer] = await ethers.getSigners();
    console.log("📝 Deploying with account:", deployer.address);

    // デプロイヤーの残高を確認
    const balance = await ethers.provider.getBalance(deployer.address);
    console.log("💰 Account balance:", ethers.formatEther(balance), "ETH");

    // MockJPYC をデプロイ
    const MockJPYC = await ethers.getContractFactory("MockJPYC");
    const jpyc = await MockJPYC.deploy();
    await jpyc.waitForDeployment();

    const jpycAddress = await jpyc.getAddress();
    console.log("✅ MockJPYC deployed to:", jpycAddress);

    // デプロイヤーに初期トークンをミント（テスト用に1,000,000 JPYC）
    const initialMint = ethers.parseEther("1000000");
    console.log("🪙 Minting initial tokens to deployer...");
    const mintTx = await jpyc.mint(deployer.address, initialMint);
    await mintTx.wait();
    console.log("✅ Minted", ethers.formatEther(initialMint), "JPYC to", deployer.address);

    // デプロイ情報を表示
    console.log("\n📋 Deployment Summary:");
    console.log("====================");
    console.log("MockJPYC Address:", jpycAddress);
    console.log("Deployer Address:", deployer.address);
    console.log("Initial Supply:", ethers.formatEther(initialMint), "JPYC");
    console.log("\n💡 Next Steps:");
    console.log("1. Update backend/.env with:");
    console.log(`   JPYC_CONTRACT_ADDRESS=${jpycAddress}`);
    console.log("2. Verify the contract on Etherscan (optional):");
    console.log(`   npx hardhat verify --network sepolia ${jpycAddress}`);
}

main()
    .then(() => process.exit(0))
    .catch((error) => {
        console.error(error);
        process.exit(1);
    });
