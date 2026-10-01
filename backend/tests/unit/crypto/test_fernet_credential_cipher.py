import pytest
from cryptography.fernet import Fernet

from app.domain.errors import CredentialServiceUnavailable
from app.infrastructure.crypto.fernet_credential_cipher import FernetCredentialCipher


def test_cipher_encrypts_and_rotated_ring_decrypts_without_plaintext():
    old, new = Fernet.generate_key().decode(), Fernet.generate_key().decode()
    original = FernetCredentialCipher([old])
    ciphertext = original.encrypt("sentinel-token")
    assert b"sentinel-token" not in ciphertext
    assert FernetCredentialCipher([new, old]).decrypt(ciphertext) == "sentinel-token"
    assert FernetCredentialCipher([new, old]).encrypt("next") != b"next"


@pytest.mark.parametrize("keys", [[], ["malformed"]])
def test_missing_or_invalid_key_ring_fails_safely(keys):
    with pytest.raises(CredentialServiceUnavailable) as caught:
        FernetCredentialCipher(keys)
    assert "malformed" not in str(caught.value)
