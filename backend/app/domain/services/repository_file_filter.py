EXCLUDED_PATH_SEGMENTS = frozenset({".git", "node_modules", "vendor", "bin", "obj", "dist", "build"})


def metadata_eligible(path: str) -> bool:
    """Metadata eligibility excludes directories and paths with an excluded exact segment."""
    parts = path.replace("\\", "/").split("/")
    return bool(parts[-1]) and not any(part.casefold() in EXCLUDED_PATH_SEGMENTS for part in parts)


def text_content_eligible(file_size: int | None, max_file_bytes: int, binary: bool | None) -> bool:
    """Future text rules must reject oversized and known-binary content before consuming it."""
    return (file_size is None or file_size <= max_file_bytes) and binary is False
