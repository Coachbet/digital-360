from adgi360.infrastructure.secrets import decrypt_secret, encrypt_secret


def test_secret_round_trip_does_not_store_plaintext():
    raw = "jeton-meta-tres-secret"

    encrypted = encrypt_secret(raw)

    assert encrypted != raw
    assert raw not in encrypted
    assert decrypt_secret(encrypted) == raw
