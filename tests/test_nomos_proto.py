import unittest

from nomos_proto import (
    AtomicSwapTemplate,
    RadioEnvelope,
    WebOfTrust,
    pow_epoch_personalization,
)


class RadioEnvelopeTests(unittest.TestCase):
    def test_roundtrip_base64(self):
        env = RadioEnvelope(
            txid="ab" * 32,
            witness_fragments=["w1", "w2"],
            nonce=7,
            expires_at_height=101,
            operator_pubkey="opk",
            created_at_unix=1700000000,
        )
        payload = env.to_b64()
        decoded = RadioEnvelope.from_b64(payload)
        self.assertEqual(env, decoded)


class WebOfTrustTests(unittest.TestCase):
    def test_attestation_and_penalty(self):
        wot = WebOfTrust()
        wot.attest("root", "alice", 1.0)
        wot.attest("root", "bob", 1.0)
        wot.penalize("bob", 0.4)
        scores = wot.score(["root"], rounds=1)
        self.assertGreater(scores["alice"], scores["bob"])


class PowTests(unittest.TestCase):
    def test_personalization_changes_with_epoch(self):
        p1 = pow_epoch_personalization("00" * 32, 2000, epoch_len=1000)
        p2 = pow_epoch_personalization("00" * 32, 3000, epoch_len=1000)
        self.assertNotEqual(p1, p2)


class AtomicSwapTests(unittest.TestCase):
    def test_valid_terms(self):
        tpl = AtomicSwapTemplate(
            sidechain_a="contracts",
            sidechain_b="payments",
            hashlock_hex="ab" * 16,
            timelock_a=144,
            timelock_b=72,
        )
        a, b = tpl.htlc_terms()
        self.assertIn("contracts", a)
        self.assertIn("payments", b)

    def test_invalid_timelocks(self):
        tpl = AtomicSwapTemplate(
            sidechain_a="a",
            sidechain_b="b",
            hashlock_hex="ab" * 16,
            timelock_a=50,
            timelock_b=50,
        )
        with self.assertRaises(ValueError):
            tpl.validate()


if __name__ == "__main__":
    unittest.main()
