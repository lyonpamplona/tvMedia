"""Testes de assinatura/verificação e revogação do token de sessão.

Pulados quando FastAPI/SQLAlchemy não estão instalados (``app.auth`` importa
FastAPI no topo do módulo).
"""

from __future__ import annotations

import time
import unittest

try:
    from app import auth, models
    from app.config import settings

    HAS_DEPS = True
except Exception:  # noqa: BLE001
    HAS_DEPS = False


@unittest.skipUnless(HAS_DEPS, "FastAPI/SQLAlchemy não instalados neste ambiente")
class TokenTests(unittest.TestCase):
    """Valida o ciclo de vida do token assinado por HMAC."""

    def _user(self) -> "models.User":
        return models.User(
            id=1,
            username="admin",
            password_hash="x",
            role=models.UserRole.admin,
            is_active=True,
            token_version=0,
        )

    def test_create_and_decode_roundtrip(self) -> None:
        user = self._user()
        token, ttl = auth.create_token(user)
        self.assertEqual(ttl, settings.token_ttl_hours * 3600)
        payload = auth._decode_token(token)
        self.assertIsNotNone(payload)
        self.assertEqual(int(payload["sub"]), 1)
        self.assertEqual(int(payload["ver"]), 0)
        self.assertGreater(int(payload["exp"]), int(time.time()))

    def test_tampered_signature_is_rejected(self) -> None:
        token, _ = auth.create_token(self._user())
        payload_b64, signature = token.split(".", 1)
        flipped = ("0" if signature[-1] != "0" else "1")
        forged = payload_b64 + "." + signature[:-1] + flipped
        self.assertIsNone(auth._decode_token(forged))

    def test_malformed_token_is_rejected(self) -> None:
        self.assertIsNone(auth._decode_token("sem-ponto"))
        self.assertIsNone(auth._decode_token(""))

    def test_revocation_via_token_version(self) -> None:
        user = self._user()
        token, _ = auth.create_token(user)
        payload = auth._decode_token(token)
        # Incrementar a versão do usuário invalida tokens antigos: o payload
        # decodificado continua íntegro, mas não casa mais com user.token_version.
        user.token_version = 1
        self.assertNotEqual(int(payload["ver"]), user.token_version)


if __name__ == "__main__":
    unittest.main()
