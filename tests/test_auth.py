import unittest

from sql_power_hour.auth import TokenVault, UserToken


class TokenVaultTests(unittest.TestCase):
    def test_token_round_trips_without_being_stored_as_plaintext(self) -> None:
        token = UserToken(
            access_token="access-secret",
            refresh_token="refresh-secret",
            expires_at=1_800_000_000,
            refresh_expires_at=1_900_000_000,
        )
        vault = TokenVault("a-long-test-session-secret")

        encrypted = vault.seal(token)

        self.assertNotIn("access-secret", encrypted)
        self.assertNotIn("refresh-secret", encrypted)
        self.assertEqual(vault.open(encrypted), token)

    def test_ciphertext_from_another_secret_is_rejected(self) -> None:
        ciphertext = TokenVault("secret-one").seal(
            UserToken("access-secret", None, None, None)
        )

        with self.assertRaisesRegex(ValueError, "session is invalid"):
            TokenVault("secret-two").open(ciphertext)


if __name__ == "__main__":
    unittest.main()
