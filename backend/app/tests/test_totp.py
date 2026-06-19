"""Testes do modulo TOTP usado no 2FA da P8."""

from __future__ import annotations

import unittest

from app import totp


class TotpTests(unittest.TestCase):
    """Valida geracao, verificacao e URL de configuracao TOTP."""

    def test_code_roundtrip_with_fixed_time(self) -> None:
        secret = "JBSWY3DPEHPK3PXP"
        original_time = totp.time.time
        try:
            totp.time.time = lambda: 1_700_000_000
            code = totp.code_at(secret)
            self.assertRegex(code, r"^\d{6}$")
            self.assertTrue(totp.verify(secret, code))
            self.assertFalse(totp.verify(secret, "000000", window=0))
        finally:
            totp.time.time = original_time

    def test_otpauth_url_contains_issuer_user_and_secret(self) -> None:
        url = totp.otpauth_url(issuer="tvMedia", username="admin", secret="ABC123")
        self.assertTrue(url.startswith("otpauth://totp/tvMedia%3Aadmin"))
        self.assertIn("secret=ABC123", url)
        self.assertIn("issuer=tvMedia", url)


if __name__ == "__main__":
    unittest.main()
