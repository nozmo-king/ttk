# Nomos: A Zcash-Derived, Radio-Relay, Multi-Sidechain Protocol

## Vision

**Nomos** is a proposed Zcash fork designed for censorship resistance, constrained-bandwidth operation, and builder-centric extensibility.

Core goals:

1. Keep Zcash-grade privacy as a first-class primitive.
2. Enable **long-range transaction relay over radio** for people without internet access.
3. Expand execution flexibility with **BIP300-style sidechains** plus primitives such as **CTV** and **CAT**.
4. Introduce a **new proof-of-work family** that avoids direct commodity SHA-256 hashrate takeover.
5. Prepare for long-term security with a **quantum-resistance migration path**.
6. Support **atomic swaps across sidechains** without centralized bridges.

## Base-Layer Parameters

### Monetary and block settings

- **Block size target:** 300 kB serialized block weight for base layer data.
- **PoW target marker:** chain branding and checkpoint references use the symbolic constant **21e8**.
- **Network profile:** tuned for low-bandwidth mempool and propagation assumptions, prioritizing transaction density over raw throughput.

### Privacy inheritance from Zcash

Nomos starts from Zcash consensus and keeps shielded transfers as default policy target. Transparent transfers remain for interoperability, but client UX should bias toward shielded pools.

## Radio Relay Architecture

Nomos introduces a low-bandwidth relay plane for transaction ingress when internet is unavailable.

### Roles

- **Offline wallet users** construct signed transactions locally.
- **Radio operators** (amateur packet, LoRa, HF gateways, mesh nodes) receive compact transaction envelopes.
- **Bridge nodes** inject verified transactions into the Nomos gossip network.
- **Core validators** treat these transactions identically to internet-relayed traffic.

### Transaction envelope format

Radio envelopes should be compact and forward-error tolerant:

- Transaction ID + minimal witness fragments.
- Optional fountain/FEC chunks for lossy links.
- Replay-protection nonce and expiration height.
- Operator signature metadata (optional reputational layer only, never consensus-critical).

### Long-range behavior

To reach "closest node hundreds of miles away," Nomos relies on a federation of independent radio relays:

- HF store-and-forward for long-distance burst propagation.
- Regional packet mesh for local aggregation.
- Opportunistic gateway uplinks to internet-connected full nodes.

This is a **mempool transport feature**, not a separate consensus mode.

## Web of Trust Overlay

Nomos includes a non-consensus **web-of-trust (WoT)** reputation graph used for relay quality and anti-spam heuristics.

- Operators attest keys for other operators.
- Nodes can weight inbound radio-origin transactions by trust score.
- Invalid or abusive relays lose score via local policy.
- Consensus remains objective: valid blocks/transactions are accepted regardless of WoT status.

This preserves permissionlessness while still helping resource-constrained radio links resist spam.

## Sidechains and Builder Primitives

Nomos uses a two-way-peg model inspired by **BIP300 drivechains**.

### Sidechain model

- Registration transaction defines sidechain ID and withdrawal parameters.
- Blind merged mining (or equivalent notarization) secures sidechain headers.
- Deterministic withdrawal bundles are ratified under defined delay windows.

### Script and covenant upgrades

Nomos base layer should include:

- **CTV (CheckTemplateVerify)** for congestion-controlled commitments and vault patterns.
- **CAT (OP_CAT)** for more expressive script composition.
- Related introspection opcodes needed to make covenant designs practical.

### Atomic swaps between sidechains

Nomos standardizes inter-sidechain swaps using HTLC/PTLC-style constructions:

- Shared hash/preimage (or adaptor signature) commitments.
- Relative timelocks with deterministic refund paths.
- Optional watchtower relays over radio for timeout enforcement signals.

No trusted bridge custodian is required.

## Proof of Work Redesign

Nomos must use a PoW algorithm family that is not trivially vulnerable to external SHA-256 miners.

### Design constraints

- **Non-SHA-256 dominance:** no drop-in reuse of Bitcoin ASIC fleets.
- **Memory hardness:** meaningful RAM bandwidth pressure to reduce pure hashing advantage.
- **Verifiable efficiently:** full nodes validate quickly relative to mining cost.
- **Parameter agility:** bounded hard-fork schedule for algorithm refresh if capture risk emerges.

### Candidate direction

A practical path is a memory-hard PoW (RandomX/ProgPoW-style philosophy, but chain-specific) with per-epoch personalization keys derived from recent block history. This raises the cost of specialized external attacks and keeps verification simple.

## Quantum Resistance Strategy

Nomos adopts staged post-quantum readiness rather than immediate forced migration.

### Phase plan

1. Add PQ-capable address types (hybrid classical + PQ signatures).
2. Introduce shielded key upgrade tooling and wallet migration UX.
3. Set long deprecation windows for legacy transparent signature schemes.
4. Offer script templates for time-locked migration vaults.

This avoids abrupt ecosystem breakage while reducing long-horizon cryptographic risk.

## Governance and Upgrade Process

- Transparent RFC process with reference implementations.
- Fixed activation cadence with public testnet rehearsals.
- Emergency patch route limited to critical consensus failures.
- Social legitimacy anchored in open client diversity and reproducible builds.

## Minimal Launch Roadmap

### Milestone 0 — Spec freeze

- Finalize consensus delta against upstream Zcash.
- Publish PoW and radio envelope specs.
- Deliver threat model and formal invariants.

### Milestone 1 — Testnet Alpha

- 300 kB block enforcement.
- Radio-to-mempool bridge reference daemon.
- WoT relay scoring as opt-in node policy.

### Milestone 2 — Sidechain + covenant beta

- BIP300-style peg prototype.
- CTV/CAT activation on testnet.
- Atomic swap reference flow between two demo sidechains.

### Milestone 3 — Mainnet genesis

- Independent genesis with auditable build pipeline.
- Multi-client launch set.
- Public radio relay map and operator docs.

## Risks and Tradeoffs

- 300 kB blocks improve low-bandwidth propagation but cap base-layer throughput.
- WoT can bias relay policy if implementations are careless.
- Drivechain designs remain socially and technically contentious.
- Novel PoW brings security unknowns until battle-tested.
- Quantum-ready cryptography may increase transaction size and verification costs.

Nomos therefore should launch with explicit conservatism: small consensus surface, aggressive testnets, and tight specification discipline.
