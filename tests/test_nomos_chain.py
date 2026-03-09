import json
import tempfile
import unittest
from pathlib import Path

from nomos_chain import MAX_BLOCK_BYTES, NomosChain
from nomos_proto import RadioEnvelope


class NomosChainTests(unittest.TestCase):
    def test_init_mine_validate_and_persistence(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "chain.json"
            chain = NomosChain(str(path))
            chain.create_genesis(difficulty=2)
            chain.submit_tx("genesis", "alice", 1000, memo="fund")
            block = chain.mine("miner1")
            self.assertEqual(block.height, 1)
            chain.save()

            loaded = NomosChain(str(path))
            loaded.load()
            loaded.validate_chain()
            self.assertEqual(loaded.height, 1)
            self.assertEqual(loaded.accounts["alice"], 1000)

    def test_block_respects_300kb_limit(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "chain.json"
            chain = NomosChain(str(path))
            chain.create_genesis(difficulty=1)
            memo_size = 2048
            for i in range(1000):
                try:
                    chain.submit_tx("genesis", f"u{i}", 1, memo="x" * memo_size)
                except ValueError:
                    break
            block = chain.mine("miner")
            tx_json = json.dumps([t.__dict__ for t in block.txs], separators=(",", ":"), sort_keys=True).encode()
            self.assertLessEqual(len(tx_json), MAX_BLOCK_BYTES)

    def test_submit_radio_envelope(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "chain.json"
            chain = NomosChain(str(path))
            chain.create_genesis(difficulty=1)
            env = RadioEnvelope(
                txid="ab" * 32,
                witness_fragments=["part1"],
                nonce=1,
                expires_at_height=5,
                operator_pubkey="operator-key",
                created_at_unix=1700000000,
            )
            tx = chain.submit_radio_envelope(env.to_b64())
            self.assertEqual(tx.sender, "operator-key")
            self.assertTrue(tx.memo.startswith("radio:"))


if __name__ == "__main__":
    unittest.main()
