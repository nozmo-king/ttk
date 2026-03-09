#!/usr/bin/env python3
"""Executable toy blockchain for the Nomos concept.

This is a runnable, educational chain implementation with:
- 300 kB maximum serialized block size
- epoch-personalized PoW using BLAKE2b + memory mixing
- basic transaction pool + mining
- radio envelope transaction ingestion

It is not production safe and does not implement full Zcash semantics.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from dataclasses import asdict, dataclass, field
from hashlib import blake2b
from pathlib import Path
from typing import Dict, List

from nomos_proto import RadioEnvelope, pow_epoch_personalization

MAX_BLOCK_BYTES = 300 * 1024
DEFAULT_CHAIN_PATH = "nomos_chain.json"


@dataclass
class Transaction:
    sender: str
    recipient: str
    amount: int
    nonce: int
    memo: str = ""
    txid: str = ""
    timestamp: int = field(default_factory=lambda: int(time.time()))

    def compute_txid(self) -> str:
        payload = json.dumps(
            {
                "sender": self.sender,
                "recipient": self.recipient,
                "amount": self.amount,
                "nonce": self.nonce,
                "memo": self.memo,
                "timestamp": self.timestamp,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return blake2b(payload, digest_size=32).hexdigest()


@dataclass
class Block:
    height: int
    prev_hash: str
    timestamp: int
    miner: str
    difficulty: int
    personalization: str
    nonce: int = 0
    txs: List[Transaction] = field(default_factory=list)
    merkle_root: str = ""
    hash: str = ""

    def header_bytes(self) -> bytes:
        header = {
            "height": self.height,
            "prev_hash": self.prev_hash,
            "timestamp": self.timestamp,
            "miner": self.miner,
            "difficulty": self.difficulty,
            "personalization": self.personalization,
            "nonce": self.nonce,
            "merkle_root": self.merkle_root,
        }
        return json.dumps(header, sort_keys=True, separators=(",", ":")).encode("utf-8")


class NomosChain:
    def __init__(self, chain_path: str = DEFAULT_CHAIN_PATH) -> None:
        self.chain_path = Path(chain_path)
        self.difficulty = 3
        self.chain: List[Block] = []
        self.mempool: List[Transaction] = []
        self.accounts: Dict[str, int] = {}
        self.nonces: Dict[str, int] = {}

    def create_genesis(self, difficulty: int = 3) -> None:
        self.difficulty = difficulty
        genesis = Block(
            height=0,
            prev_hash="0" * 64,
            timestamp=int(time.time()),
            miner="genesis",
            difficulty=difficulty,
            personalization="nomos|21e8|genesis",
            nonce=0,
            txs=[],
            merkle_root=blake2b(b"genesis", digest_size=32).hexdigest(),
        )
        genesis.hash = self._pow_hash(genesis)
        self.chain = [genesis]
        self.mempool = []
        self.accounts = {"genesis": 21_000_000_000}
        self.nonces = {"genesis": 0}

    def load(self) -> None:
        if not self.chain_path.exists():
            raise FileNotFoundError(f"chain file not found: {self.chain_path}")
        data = json.loads(self.chain_path.read_text())
        self.difficulty = int(data["difficulty"])
        self.accounts = {k: int(v) for k, v in data.get("accounts", {}).items()}
        self.nonces = {k: int(v) for k, v in data.get("nonces", {}).items()}
        self.mempool = [Transaction(**tx) for tx in data.get("mempool", [])]
        self.chain = []
        for raw_block in data["chain"]:
            txs = [Transaction(**tx) for tx in raw_block["txs"]]
            block = Block(
                height=raw_block["height"],
                prev_hash=raw_block["prev_hash"],
                timestamp=raw_block["timestamp"],
                miner=raw_block["miner"],
                difficulty=raw_block["difficulty"],
                personalization=raw_block["personalization"],
                nonce=raw_block["nonce"],
                txs=txs,
                merkle_root=raw_block["merkle_root"],
                hash=raw_block["hash"],
            )
            self.chain.append(block)

    def save(self) -> None:
        payload = {
            "difficulty": self.difficulty,
            "accounts": self.accounts,
            "nonces": self.nonces,
            "mempool": [asdict(tx) for tx in self.mempool],
            "chain": [
                {
                    "height": b.height,
                    "prev_hash": b.prev_hash,
                    "timestamp": b.timestamp,
                    "miner": b.miner,
                    "difficulty": b.difficulty,
                    "personalization": b.personalization,
                    "nonce": b.nonce,
                    "txs": [asdict(tx) for tx in b.txs],
                    "merkle_root": b.merkle_root,
                    "hash": b.hash,
                }
                for b in self.chain
            ],
        }
        self.chain_path.write_text(json.dumps(payload, indent=2))

    def submit_tx(self, sender: str, recipient: str, amount: int, memo: str = "") -> Transaction:
        if amount <= 0:
            raise ValueError("amount must be positive")
        nonce = self.nonces.get(sender, 0) + 1
        tx = Transaction(sender=sender, recipient=recipient, amount=amount, nonce=nonce, memo=memo)
        tx.txid = tx.compute_txid()
        self._validate_tx(tx, include_mempool=True)
        self.mempool.append(tx)
        return tx

    def submit_radio_envelope(self, payload_b64: str) -> Transaction:
        env = RadioEnvelope.from_b64(payload_b64)
        tx = Transaction(
            sender=env.operator_pubkey or "radio-unknown",
            recipient="radio-relay",
            amount=0,
            nonce=env.nonce,
            memo=f"radio:{env.txid[:24]}",
        )
        tx.txid = tx.compute_txid()
        if self.height > env.expires_at_height:
            raise ValueError("radio envelope expired")
        self._validate_tx(tx, include_mempool=True)
        self.mempool.append(tx)
        return tx

    @property
    def height(self) -> int:
        return self.chain[-1].height if self.chain else -1

    def mine(self, miner: str) -> Block:
        if not self.chain:
            raise RuntimeError("chain is empty; initialize genesis first")
        selected = self._select_txs_for_block()
        reward = Transaction(sender="coinbase", recipient=miner, amount=50, nonce=0, memo=f"reward@{self.height + 1}")
        reward.txid = reward.compute_txid()
        txs = [reward] + selected

        block = Block(
            height=self.height + 1,
            prev_hash=self.chain[-1].hash,
            timestamp=int(time.time()),
            miner=miner,
            difficulty=self.difficulty,
            personalization=pow_epoch_personalization(self.chain[-1].hash, self.height + 1),
            txs=txs,
        )
        block.merkle_root = self._merkle_root(txs)
        target = "0" * self.difficulty

        nonce = 0
        while True:
            block.nonce = nonce
            digest = self._pow_hash(block)
            if digest.startswith(target):
                block.hash = digest
                break
            nonce += 1

        self._apply_block(block)
        self.mempool = [tx for tx in self.mempool if tx.txid not in {t.txid for t in selected}]
        self.chain.append(block)
        return block

    def validate_chain(self) -> None:
        if not self.chain:
            raise ValueError("empty chain")
        for idx, block in enumerate(self.chain):
            if idx == 0:
                continue
            prev = self.chain[idx - 1]
            if block.prev_hash != prev.hash:
                raise ValueError(f"broken prev-hash at height {block.height}")
            if self._pow_hash(block) != block.hash:
                raise ValueError(f"bad hash at height {block.height}")
            if not block.hash.startswith("0" * block.difficulty):
                raise ValueError(f"insufficient PoW at height {block.height}")
            if len(self._serialize_txs(block.txs)) > MAX_BLOCK_BYTES:
                raise ValueError(f"block exceeds 300 kB at height {block.height}")

    def _pow_hash(self, block: Block) -> str:
        # memory-mixed hashing step (educational only)
        seed = blake2b(block.header_bytes(), digest_size=32).digest()
        scratch = bytearray(seed * 64)
        for i in range(0, len(scratch), 32):
            h = blake2b(
                block.personalization.encode("utf-8") + scratch[i : i + 32] + block.nonce.to_bytes(8, "little"),
                digest_size=32,
            ).digest()
            scratch[i : i + 32] = h
        return blake2b(bytes(scratch), digest_size=32).hexdigest()

    def _serialize_txs(self, txs: List[Transaction]) -> bytes:
        return json.dumps([asdict(tx) for tx in txs], separators=(",", ":"), sort_keys=True).encode("utf-8")

    def _select_txs_for_block(self) -> List[Transaction]:
        picked: List[Transaction] = []
        size = 2  # for []
        for tx in self.mempool:
            tx_bytes = json.dumps(asdict(tx), separators=(",", ":"), sort_keys=True).encode("utf-8")
            # +1 for comma separator safety
            if size + len(tx_bytes) + 1 > MAX_BLOCK_BYTES:
                break
            self._validate_tx(tx, include_mempool=False)
            picked.append(tx)
            size += len(tx_bytes) + 1
        return picked

    def _validate_tx(self, tx: Transaction, include_mempool: bool) -> None:
        if tx.sender != "coinbase":
            balance = self.accounts.get(tx.sender, 0)
            pending = 0
            if include_mempool:
                pending = sum(t.amount for t in self.mempool if t.sender == tx.sender)
            if balance - pending < tx.amount:
                raise ValueError("insufficient balance")
            expected = self.nonces.get(tx.sender, 0) + 1
            if tx.nonce != expected:
                raise ValueError(f"bad nonce: expected {expected}, got {tx.nonce}")

    def _apply_block(self, block: Block) -> None:
        for tx in block.txs:
            if tx.sender != "coinbase":
                self.accounts[tx.sender] = self.accounts.get(tx.sender, 0) - tx.amount
                self.nonces[tx.sender] = tx.nonce
            self.accounts[tx.recipient] = self.accounts.get(tx.recipient, 0) + tx.amount

    @staticmethod
    def _merkle_root(txs: List[Transaction]) -> str:
        if not txs:
            return blake2b(b"", digest_size=32).hexdigest()
        layer = [bytes.fromhex(t.txid) for t in txs]
        while len(layer) > 1:
            if len(layer) % 2 == 1:
                layer.append(layer[-1])
            layer = [blake2b(layer[i] + layer[i + 1], digest_size=32).digest() for i in range(0, len(layer), 2)]
        return layer[0].hex()


def _load_or_die(path: str) -> NomosChain:
    chain = NomosChain(path)
    chain.load()
    return chain


def cmd_init(args: argparse.Namespace) -> None:
    chain = NomosChain(args.path)
    if Path(args.path).exists() and not args.force:
        raise FileExistsError(f"{args.path} exists (pass --force to overwrite)")
    chain.create_genesis(difficulty=args.difficulty)
    chain.save()
    print(f"initialized Nomos chain at {args.path} (difficulty={args.difficulty})")


def cmd_submit_tx(args: argparse.Namespace) -> None:
    chain = _load_or_die(args.path)
    tx = chain.submit_tx(args.sender, args.recipient, args.amount, memo=args.memo)
    chain.save()
    print(f"queued tx {tx.txid}")


def cmd_submit_radio(args: argparse.Namespace) -> None:
    chain = _load_or_die(args.path)
    tx = chain.submit_radio_envelope(args.payload)
    chain.save()
    print(f"queued radio tx {tx.txid}")


def cmd_mine(args: argparse.Namespace) -> None:
    chain = _load_or_die(args.path)
    block = chain.mine(args.miner)
    chain.save()
    print(f"mined block height={block.height} hash={block.hash} txs={len(block.txs)}")


def cmd_validate(args: argparse.Namespace) -> None:
    chain = _load_or_die(args.path)
    chain.validate_chain()
    print(f"chain valid: height={chain.height} blocks={len(chain.chain)}")


def cmd_show(args: argparse.Namespace) -> None:
    chain = _load_or_die(args.path)
    summary = {
        "height": chain.height,
        "difficulty": chain.difficulty,
        "mempool": len(chain.mempool),
        "tip_hash": chain.chain[-1].hash,
        "accounts": chain.accounts,
    }
    print(json.dumps(summary, indent=2, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Nomos executable toy blockchain")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("init")
    p.add_argument("--path", default=DEFAULT_CHAIN_PATH)
    p.add_argument("--difficulty", type=int, default=3)
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("submit-tx")
    p.add_argument("--path", default=DEFAULT_CHAIN_PATH)
    p.add_argument("--sender", required=True)
    p.add_argument("--recipient", required=True)
    p.add_argument("--amount", type=int, required=True)
    p.add_argument("--memo", default="")
    p.set_defaults(func=cmd_submit_tx)

    p = sub.add_parser("submit-radio")
    p.add_argument("--path", default=DEFAULT_CHAIN_PATH)
    p.add_argument("--payload", required=True)
    p.set_defaults(func=cmd_submit_radio)

    p = sub.add_parser("mine")
    p.add_argument("--path", default=DEFAULT_CHAIN_PATH)
    p.add_argument("--miner", required=True)
    p.set_defaults(func=cmd_mine)

    p = sub.add_parser("validate")
    p.add_argument("--path", default=DEFAULT_CHAIN_PATH)
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("show")
    p.add_argument("--path", default=DEFAULT_CHAIN_PATH)
    p.set_defaults(func=cmd_show)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
