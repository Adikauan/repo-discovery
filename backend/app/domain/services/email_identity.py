import re
try:
    from email_validator import EmailNotValidError, validate_email
except ImportError:
    EmailNotValidError = ValueError
    class _Validated:
        def __init__(self, normalized): self.normalized = normalized
    def validate_email(value, *, check_deliverability=False):
        if not re.fullmatch(r"[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+", value):
            raise EmailNotValidError("invalid email")
        return _Validated(value)


def normalized_email(value: str) -> str:
    return validate_email(value.strip(), check_deliverability=False).normalized.casefold()


def is_valid_email(value: str) -> bool:
    try:
        normalized_email(value)
        return True
    except (EmailNotValidError, ValueError):
        return False
