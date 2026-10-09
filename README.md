# ⚡ Continuum Network ($CTM$) — Next-Gen Gasless L2 EVM Protocol

**Continuum Network** is a high-performance Layer-2 EVM execution environment built on Base Sepolia. Designed to eliminate web3 onboarding friction, Continuum integrates an **ERC-4337 Token-Paymaster**, **ERC-2612 Gasless Permits**, and **Deflationary Gas Burning Mechanics** to deliver a $0$ ETH gas user experience.

## 🌟 Key Features

* **⚡ Zero-ETH Gas User Experience:** Users interact with DApps and transfer assets using $CTM$ tokens via automated ERC-4337 Paymaster sponsorship.
* **🔥 Deflationary Tokenomics:** $50\%$ of all $CTM$ gas fees collected per transaction are permanently burned from total supply.
* **🛡️ Anti-Sybil Protection:** Sequencer-level rate-limiting requiring a minimum balance threshold of $100\ \text{CTM}$ and daily transaction quotas per address.
* **🏆 Dual-Tier NFT Ecosystem:** Includes the non-transferable **OG Pioneer Soulbound NFT** for testnet contributors and the unique **1/1 Genesis Founder NFT** for leaderboard champions.
* **🌐 ISO 20022 Financial Gateway:** Native mapping (`pacs.008`) for institutional asset tokenization and cross-chain financial messaging.

## 📜 Verified Smart Contracts (Base Sepolia)

| Contract | Address | Explorer Link |
| --- | --- | --- |
| **$CTM$ Token (ERC-20)** | `0x078712Ac537F24B76a1AAB05624c02A9E0a28C13` | [View on Basescan](https://sepolia.basescan.org/token/0x078712Ac537F24B76a1AAB05624c02A9E0a28C13) |
| **Pioneer NFT (ERC-721)** | `0x759Acd678668DbdF08df0B59aEEc5E9577F3BD2D` | [View on Basescan](https://sepolia.basescan.org/address/0x759Acd678668DbdF08df0B59aEEc5E9577F3BD2D) |

## 📂 Repository Structure

```
├── assets/                  # High-resolution 3D NFT & Branding artwork
├── contracts/               # Solidity Smart Contracts (ERC-20, ERC-721, Paymaster)
├── docs/                    # Technical Architecture & Tokenomics documentation
│   ├── architecture.md      # Deep dive into Paymaster & L2 engine
│   └── tokenomics.md        # Token distribution, burn, and NFT utility
├── metadata/                # On-chain JSON metadata for OG Pioneer & Genesis NFTs
├── index.html               # Telegram Mini App & Web3 DApp interface
└── README.md                # Project Overview
```

## 🚀 Quick Start (Local Setup)

1. Clone the repository:
   ```bash
   git clone https://github.com/0xContinuum/continuum-network-l2.git
   cd continuum-network-l2
   ```

2. Serve the DApp locally:
   ```bash
   npx serve .
   ```

3. Open `http://localhost:3000` in your browser or launch via Telegram Mini App.

## 📄 Documentation & Links

* **Technical Architecture**: See [`docs/architecture.md`](./docs/architecture.md)
* **Tokenomics & NFTs**: See [`docs/tokenomics.md`](./docs/tokenomics.md)
* **DApp Portal**: [Continuum Telegram Mini App](https://t.me/ContinuumCTM_bot)