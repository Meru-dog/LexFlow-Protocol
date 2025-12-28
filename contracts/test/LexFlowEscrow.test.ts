import { expect } from "chai"; // Chaiのユーティリティ
import { ethers } from "hardhat"; // Hardhatのユーティリティ
import { LexFlowEscrow, MockJPYC } from "../typechain-types"; // コントラクトの型定義
import { HardhatEthersSigner } from "@nomicfoundation/hardhat-ethers/signers"; // シグナーの型定義

// LexFlowEscrowのテスト
describe("LexFlowEscrow", function () {
    let escrow: LexFlowEscrow; // LexFlowEscrowコントラクト
    let jpyc: MockJPYC; // MockJPYCコントラクト
    let payer: HardhatEthersSigner; // Payer
    let lawyer: HardhatEthersSigner; // Lawyer
    let payee: HardhatEthersSigner; // Payee

    const CONTRACT_ID = ethers.keccak256(ethers.toUtf8Bytes("contract-1")); // 契約ID
    const CONDITION_ID = ethers.keccak256(ethers.toUtf8Bytes("condition-1")); // 条件ID
    const EVIDENCE_HASH = ethers.keccak256(ethers.toUtf8Bytes("evidence-data")); // 調査証拠データ
    const ESCROW_AMOUNT = ethers.parseEther("100000"); // 100,000 JPYC
    const CONDITION_AMOUNT = ethers.parseEther("50000"); // 50,000 JPYC

    // 各テストケースの前に実行される
    beforeEach(async function () {
        [payer, lawyer, payee] = await ethers.getSigners();

        // MockJPYCのデプロイ
        const MockJPYC = await ethers.getContractFactory("MockJPYC");
        jpyc = await MockJPYC.deploy();
        await jpyc.waitForDeployment();

        // LexFlowEscrowのデプロイ
        const LexFlowEscrow = await ethers.getContractFactory("LexFlowEscrow");
        escrow = await LexFlowEscrow.deploy(await jpyc.getAddress());
        await escrow.waitForDeployment();

        // PayerがEscrowにJPYCをApprove
        await jpyc.connect(payer).approve(await escrow.getAddress(), ESCROW_AMOUNT);
    });

    // コントラクトの作成
    describe("Contract Creation", function () {
        it("should create a contract with escrow funds", async function () {
            // コントラクトの作成
            await expect(escrow.connect(payer).createContract(CONTRACT_ID, lawyer.address, ESCROW_AMOUNT))
                .to.emit(escrow, "ContractCreated")
                .withArgs(CONTRACT_ID, payer.address, lawyer.address, ESCROW_AMOUNT);
            // コントラクトの取得
            const contract = await escrow.getContract(CONTRACT_ID);
            expect(contract.payer).to.equal(payer.address);
            expect(contract.lawyer).to.equal(lawyer.address);
            expect(contract.totalAmount).to.equal(ESCROW_AMOUNT);
            expect(contract.isActive).to.be.true;
        });

        it("should transfer JPYC to escrow", async function () {
            // 初期残高の取得
            const initialBalance = await jpyc.balanceOf(payer.address);
            // コントラクトの作成
            await escrow.connect(payer).createContract(CONTRACT_ID, lawyer.address, ESCROW_AMOUNT);
            // 最終残高の取得
            const finalBalance = await jpyc.balanceOf(payer.address);
            // 残高の確認
            expect(initialBalance - finalBalance).to.equal(ESCROW_AMOUNT);
            expect(await jpyc.balanceOf(await escrow.getAddress())).to.equal(ESCROW_AMOUNT);
        });
    });

    // 条件の管理
    describe("Condition Management", function () {
        beforeEach(async function () {
            // コントラクトの作成
            await escrow.connect(payer).createContract(CONTRACT_ID, lawyer.address, ESCROW_AMOUNT);
        });

        it("should add a condition", async function () {
            // 条件の追加
            await expect(escrow.connect(payer).addCondition(CONTRACT_ID, CONDITION_ID, payee.address, CONDITION_AMOUNT))
                .to.emit(escrow, "ConditionAdded")
                .withArgs(CONTRACT_ID, CONDITION_ID, payee.address, CONDITION_AMOUNT);

            // 条件の取得
            const condition = await escrow.getCondition(CONTRACT_ID, CONDITION_ID);
            expect(condition.payee).to.equal(payee.address);
            expect(condition.amount).to.equal(CONDITION_AMOUNT);
            expect(condition.status).to.equal(0); // Pending
        });

        it("should submit evidence for a condition", async function () {
            // 条件の追加
            await escrow.connect(payer).addCondition(CONTRACT_ID, CONDITION_ID, payee.address, CONDITION_AMOUNT);
            // 調査証拠の提出
            await expect(escrow.submitEvidence(CONTRACT_ID, CONDITION_ID, EVIDENCE_HASH))
                .to.emit(escrow, "EvidenceSubmitted")
                .withArgs(CONTRACT_ID, CONDITION_ID, EVIDENCE_HASH);
            // 条件の状態を取得
            const condition = await escrow.getCondition(CONTRACT_ID, CONDITION_ID);
            expect(condition.status).to.equal(1); // Judging
            expect(condition.evidenceHash).to.equal(EVIDENCE_HASH);
        });
    });

    // 承認と支払い
    describe("Approval and Payment", function () {
        beforeEach(async function () {
            // コントラクトの作成
            await escrow.connect(payer).createContract(CONTRACT_ID, lawyer.address, ESCROW_AMOUNT);
            // 条件の追加
            await escrow.connect(payer).addCondition(CONTRACT_ID, CONDITION_ID, payee.address, CONDITION_AMOUNT);
            // 調査証拠の提出
            await escrow.submitEvidence(CONTRACT_ID, CONDITION_ID, EVIDENCE_HASH);
        });

        it("should approve condition and execute payment", async function () {
            const initialPayeeBalance = await jpyc.balanceOf(payee.address);
            // 条件の承認
            await expect(escrow.connect(lawyer).approveCondition(CONTRACT_ID, CONDITION_ID))
                .to.emit(escrow, "ConditionApproved")
                .withArgs(CONTRACT_ID, CONDITION_ID)
                .to.emit(escrow, "PaymentExecuted")
                .withArgs(CONTRACT_ID, CONDITION_ID, payee.address, CONDITION_AMOUNT);
            // 条件の状態を取得
            const condition = await escrow.getCondition(CONTRACT_ID, CONDITION_ID);
            expect(condition.status).to.equal(3); // Executed
            // 支払先の残高を取得
            const finalPayeeBalance = await jpyc.balanceOf(payee.address);
            expect(finalPayeeBalance - initialPayeeBalance).to.equal(CONDITION_AMOUNT);
        });

        it("should reject condition", async function () {
            // 条件の拒否
            await expect(escrow.connect(lawyer).rejectCondition(CONTRACT_ID, CONDITION_ID))
                .to.emit(escrow, "ConditionRejected")
                .withArgs(CONTRACT_ID, CONDITION_ID);
            // 条件の状態を取得
            const condition = await escrow.getCondition(CONTRACT_ID, CONDITION_ID);
            expect(condition.status).to.equal(4); // Rejected
        });

        it("should only allow lawyer to approve", async function () {
            // 条件の承認
            await expect(escrow.connect(payer).approveCondition(CONTRACT_ID, CONDITION_ID))
                .to.be.revertedWith("LexFlow: caller is not the lawyer");
        });
    });

    // 全ての流れ
    describe("Full Flow", function () {
        it("should complete full escrow flow: create → add condition → evidence → approve → pay", async function () {
            // 1. コントラクトの作成
            await escrow.connect(payer).createContract(CONTRACT_ID, lawyer.address, ESCROW_AMOUNT);

            // 2. 条件の追加
            await escrow.connect(payer).addCondition(CONTRACT_ID, CONDITION_ID, payee.address, CONDITION_AMOUNT);

            // 3. 調査証拠の提出
            await escrow.submitEvidence(CONTRACT_ID, CONDITION_ID, EVIDENCE_HASH);

            // 4. 弁護士の承認
            await escrow.connect(lawyer).approveCondition(CONTRACT_ID, CONDITION_ID);

            // 5. 支払いの確認
            expect(await jpyc.balanceOf(payee.address)).to.equal(CONDITION_AMOUNT);
            expect(await escrow.getEscrowBalance(CONTRACT_ID)).to.equal(ESCROW_AMOUNT - CONDITION_AMOUNT);
        });
    });
});
