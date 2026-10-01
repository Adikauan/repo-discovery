from cryptography.fernet import Fernet, InvalidToken, MultiFernet

from app.domain.errors import CredentialServiceUnavailable


class FernetCredentialCipher:
    def __init__(self, keys: list[str]):
        try:
            if not keys:
                raise ValueError("missing key ring")
            self._fernet = MultiFernet([Fernet(key.encode("ascii")) for key in keys])
        except Exception as error:
            raise CredentialServiceUnavailable("Credential encryption is unavailable.") from error

    def encrypt(self, token: str) -> bytes:
        try:
            return self._fernet.encrypt(token.encode("utf-8"))
        except Exception as error:
            raise CredentialServiceUnavailable("Credential encryption is unavailable.") from error

    def decrypt(self, encrypted_token: bytes) -> str:
        try:
            return self._fernet.decrypt(encrypted_token).decode("utf-8")
        except (InvalidToken, UnicodeError, ValueError) as error:
            raise CredentialServiceUnavailable("Credential encryption is unavailable.") from error
