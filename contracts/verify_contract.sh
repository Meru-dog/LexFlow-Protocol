#!/bin/bash
# LexFlow Protocol - Contract Verification Script
# This script helps verify the smart contract on Etherscan using the API key provided.

# Load contract address from recent deployment or provide manually
ESCROW_CONTRACT_ADDRESS=0x113B647c13d8AC3BE5218f47514E0e31eCAbA058
JPYC_CONTRACT_ADDRESS=0x7dE27D90B5188881aF44eAbB254278cc98B27966

echo "🚀 Starting contract verification on Sepolia Etherscan..."

cd contracts

# Verify LexFlowEscrow
# Parameters: Address, Constructor arguments (none for LexFlowEscrow if it uses initialized or hardcoded JPYC)
# If LexFlowEscrow has constructor args, they should be added after the address
npx hardhat verify --network sepolia $ESCROW_CONTRACT_ADDRESS

echo "✅ Verification process initiated. Check the status on Etherscan."
