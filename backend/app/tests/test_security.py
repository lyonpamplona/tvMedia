"""Testes do módulo de segurança (hashing de senha e rate limiting).

Não dependem de SQLAlchemy/FastAPI, portanto rodam em qualquer ambiente.
"""

from __future__ import annotations

import unittest

from app import security


class PasswordHashingTests(unittest.TestCase):
    """Verifica o ciclo de hash/verificação de senhas (pbkdf2_sha256)."""

    def test_hash_is_salted_and_verifiable(self) -> None:
        h1 = security.hash_password("segredo123")
        h2 = security.hash_password("segredo123")
        self.assertTrue(h1.startswith("pbkdf2_sha256$"))
        # Salts distintos => hashes distintos para a mesma senha.
        self.assertNotEqual(h1, h2)
        self.assertTrue(security.verify_password("segredo123", h1))
        self.assertTrue(security.verify_password("segredo123", h2))

    def test_verify_rejects_wrong_password(self) -> None:
        h = security.hash_password("correta")
        self.assertFalse(security.verify_password("errada", h))

    def test_verify_handles_malformed_hash(self) -> None:
        self.assertFalse(security.verify_password("x", "hash-invalido"))
        self.assertFalse(security.verify_password("x", ""))


class RateLimiterTests(unittest.TestCase):
    """Verifica o bloqueio progressivo do RateLimiter de login."""

    def test_blocks_after_max_attempts(self) -> None:
        rl = security.RateLimiter(max_attempts=3, window_seconds=100, block_seconds=100)
        key = "10.0.0.1"
        self.assertEqual(rl.retry_after(key), 0)
        rl.register_failure(key)
        rl.register_failure(key)
        self.assertEqual(rl.retry_after(key), 0)  # ainda abaixo do limite
        rl.register_failure(key)
        self.assertGreater(rl.retry_after(key), 0)  # bloqueado no 3º erro

    def test_reset_clears_block(self) -> None:
        rl = security.RateLimiter(max_attempts=2, window_seconds=100, block_seconds=100)
        key = "10.0.0.2"
        rl.register_failure(key)
        rl.register_failure(key)
        self.assertGreater(rl.retry_after(key), 0)
        rl.reset(key)
        self.assertEqual(rl.retry_after(key), 0)


if __name__ == "__main__":
    unittest.main()
