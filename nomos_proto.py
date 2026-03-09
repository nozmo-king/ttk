"""Nomos prototype primitives.

This module provides a small, runnable prototype for parts of the Nomos design:
- compact radio transaction envelopes
- a local web-of-trust scoring model for relay policy
- PoW epoch personalization helper
- sidechain atomic swap contract templates

It is intentionally non-consensus and educational.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import blake2b
import base64
import json
import time
from typing import Dict, Iterable, List, Tuple


@dataclass(frozen=True)
class RadioEnvelope:
    """Compact transaction transport envelope for radio relay hops."""

    txid: str
    witness_fragments: List[str]
    nonce: int
    expires_at_height: int
    operator_pubkey: str | None = None
    created_at_unix: int = int(time.time())

    def to_bytes(self) -> bytes:
        """Serialize to a compact JSON payload."""

        data = {
            "t": self.txid,
            "w": self.witness_fragments,
            "n": self.nonce,
            "e": self.expires_at_height,
            "k": self.operator_pubkey,
            "c": self.created_at_unix,
        }
        return json.dumps(data, separators=(",", ":")).encode("utf-8")

    def to_b64(self) -> str:
        return base64.b64encode(self.to_bytes()).decode("ascii")

    @staticmethod
    def from_b64(payload: str) -> "RadioEnvelope":
        data = json.loads(base64.b64decode(payload).decode("utf-8"))
        return RadioEnvelope(
            txid=data["t"],
            witness_fragments=list(data["w"]),
            nonce=int(data["n"]),
            expires_at_height=int(data["e"]),
            operator_pubkey=data.get("k"),
            created_at_unix=int(data["c"]),
        )


class WebOfTrust:
    """Simple non-consensus trust graph for relay policy weighting."""

    def __init__(self) -> None:
        self._attestations: Dict[str, Dict[str, float]] = {}
        self._penalties: Dict[str, float] = {}

    def attest(self, from_key: str, to_key: str, weight: float = 1.0) -> None:
        if weight <= 0:
            raise ValueError("weight must be positive")
        self._attestations.setdefault(from_key, {})[to_key] = weight

    def penalize(self, key: str, amount: float = 1.0) -> None:
        if amount < 0:
            raise ValueError("penalty must be non-negative")
        self._penalties[key] = self._penalties.get(key, 0.0) + amount

    def score(self, roots: Iterable[str], rounds: int = 3) -> Dict[str, float]:
        current: Dict[str, float] = {r: 1.0 for r in roots}

        for _ in range(rounds):
            nxt: Dict[str, float] = {}
            for src, src_score in current.items():
                edges = self._attestations.get(src, {})
                if not edges:
                    nxt[src] = nxt.get(src, 0.0) + src_score
                    continue
                total = sum(edges.values())
                for dst, w in edges.items():
                    nxt[dst] = nxt.get(dst, 0.0) + (src_score * (w / total))
            current = nxt

        for node, penalty in self._penalties.items():
            if node in current:
                current[node] = max(0.0, current[node] - penalty)
        return current


def pow_epoch_personalization(prev_block_hash_hex: str, height: int, epoch_len: int = 2016) -> str:
    """Create a deterministic epoch personalization tag.

    This can feed memory-hard PoW key schedules without reusing SHA-256 miner pipelines.
    """

    if height < 0:
        raise ValueError("height must be non-negative")
    if epoch_len <= 0:
        raise ValueError("epoch_len must be positive")

    epoch = height // epoch_len
    material = f"nomos|21e8|{epoch}|{prev_block_hash_hex}".encode("utf-8")
    return blake2b(material, digest_size=16).hexdigest()


@dataclass(frozen=True)
class AtomicSwapTemplate:
    """Swap template for sidechain-to-sidechain contracts."""

    sidechain_a: str
    sidechain_b: str
    hashlock_hex: str
    timelock_a: int
    timelock_b: int

    def validate(self) -> None:
        if self.timelock_a <= self.timelock_b:
            raise ValueError("timelock_a must be greater than timelock_b for safe refund ordering")
        if len(self.hashlock_hex) < 32:
            raise ValueError("hashlock_hex must be at least 16 bytes (32 hex chars)")

    def htlc_terms(self) -> Tuple[str, str]:
        """Return human-readable HTLC contract conditions for each sidechain."""

        self.validate()
        a = (
            f"{self.sidechain_a}: spend with preimage(hash={self.hashlock_hex}) before {self.timelock_a}, "
            f"else refund sender"
        )
        b = (
            f"{self.sidechain_b}: spend with preimage(hash={self.hashlock_hex}) before {self.timelock_b}, "
            f"else refund sender"
        )
        return a, b
