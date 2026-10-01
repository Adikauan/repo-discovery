from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RepositoryFileMetadata:
    path: str
    file_type: str = "blob"
    size_bytes: int | None = None
    binary: bool | None = None

    def __post_init__(self):
        if not self.path or self.file_type not in {"blob", "file"}:
            raise ValueError("Repository file metadata must identify a file path.")
        if self.size_bytes is not None and (type(self.size_bytes) is not int or self.size_bytes < 0):
            raise ValueError("File size must be nonnegative when available.")


@dataclass(frozen=True, slots=True)
class RepositoryContext:
    project_id: int
    repository_name: str
    repository_full_path: str
    branch: str
    files: tuple[RepositoryFileMetadata, ...]
    max_file_bytes: int = 1_048_576

    def __post_init__(self):
        if not self.branch or self.project_id <= 0 or self.max_file_bytes < 1:
            raise ValueError("Repository context requires a valid project, branch, and content limit.")
