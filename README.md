# Continuum Network ($CTM) - L2 EVM Ecosystem

Continuum Network is a Layer-2 EVM execution environment on Base built with an integrated **ERC-4337 Token-Paymaster**, **ERC-2612 Gasless Permits**, and **50% Deflationary Gas Burning Mechanics**.

## Core Features
- **Zero-ETH Gas Experience:** Users transact using $CTM tokens via ERC-4337 Token-Paymaster.
- **Deflationary Tokenomics:** 50% of $CTM gas fees collected per transaction are permanently burned.
- **Anti-Sybil Engine:** Sequencer-level rate limiting requiring a 100 $CTM minimum balance and a 2-transaction daily limit per address.
- **ISO 20022 Gateway:** Financial messaging mapping (`pacs.008`) for institutional asset tokenization.

## Architecture
- `contracts/`: Verified Solidity contracts (`ContinuumToken.sol`).
- `sequencer/`: Python L2 Sequencer and Paymaster engine (`continuum_network_3.py`).
- `explorer/`: Streamlit-based L2 Block & Analytics Explorer.

## Quick Start
1. Install dependencies:
   ```bash
   pip install -r requirements.txt