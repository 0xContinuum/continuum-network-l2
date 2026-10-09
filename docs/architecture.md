# 🛠️ Continuum Network Architecture

Continuum Network simplifies blockchain interactions by removing native gas requirements ($ETH$) and wrapping gas sponsorship natively into the protocol layer.

---

## 1. Gasless Infrastructure (ERC-4337 & Paymaster)

Traditional EVM transactions require users to hold native network tokens ($ETH$) to pay gas fees. Continuum solves this via an **ERC-4337 Account Abstraction** paymaster sponsorship pipeline:

```
[User / Telegram DApp] ──> [Sponsored Relayer / Paymaster API] ──> [Base L2 Sequencer] ──> [Continuum Smart Contracts]
```

### Transaction Flow
1. **User Initiation:** User triggers a transaction (e.g., $CTM$ transfer or NFT mint) without holding testnet $ETH$.
2. **Balance Verification:** Paymaster checks if the user balance holds $\ge 100\ \text{CTM}$.
3. **Gas Sponsorship:** The Paymaster backend sponsors native gas ($ETH$) on Base Sepolia.
4. **Execution:** The transaction is signed and broadcasted to the L2 execution layer instantly.

---

## 2. Anti-Sybil & Rate Limiting Engine

To prevent spam attacks on the testnet faucet and relayer:

- **Minimum Hold Threshold:** Users must hold a minimum balance $B \ge 100\ \text{CTM}$ to qualify for $0$ ETH sponsored transactions.
- **Daily Execution Limit:** Maximum $N = 2$ sponsored transfers per 24-hour rolling window per address.
- **Deterministic Key Derivation:** Telegram Mini App users automatically generate a secure deterministic keypair derived from their unique Telegram User ID:
  $$\text{PrivateKey} = \text{keccak256}(\text{"continuum_network_l2_salt_2026_"} + \text{TelegramUserID})$$

---

## 3. ISO 20022 Financial Gateway

Continuum bridges institutional messaging formats with EVM execution logs:

- **`pacs.008` Financial Messaging Mapping:** Credit transfer messages are parsed into structured EVM event logs.
- **Compliance & Auditability:** Allows financial institutions to trace asset tokenization settlements with cryptographic finality on Layer-2.