from dataclasses import dataclass, replace
from datetime import datetime
from typing import Literal
from uuid import UUID


FilesCompleteness = Literal["complete", "truncated", "unknown"]
ChangeType = Literal["added", "modified", "deleted", "renamed"]

MAX_DIFF_FILES = 100
MAX_DIFF_BYTES_PER_FILE = 256 * 1024
MAX_TOTAL_DIFF_BYTES = 2 * 1024 * 1024
MAX_DIFF_PATH_BYTES = 4096
MAX_REPOSITORY_NAME_BYTES = 200


def bound_utf8(value: str | None, max_bytes: int) -> tuple[str | None, bool]:
    if value is None:
        return None, False
    raw = value.encode("utf-8")
    if len(raw) <= max_bytes:
        return value, False
    clipped = raw[:max_bytes]
    while clipped:
        try:
            return clipped.decode("utf-8"), True
        except UnicodeDecodeError:
            clipped = clipped[:-1]
    return "", True


@dataclass(frozen=True, slots=True)
class CommitDiffFile:
    old_path: str | None
    new_path: str | None
    change_type: ChangeType | None
    diff: str | None
    text_diff_available: bool
    binary: bool | None = None
    collapsed: bool | None = None
    too_large: bool | None = None
    diff_truncated: bool = False
    old_path_truncated: bool = False
    new_path_truncated: bool = False


@dataclass(frozen=True, slots=True)
class CommitDiffProviderResult:
    files: tuple[CommitDiffFile, ...]
    files_completeness: FilesCompleteness

    def __post_init__(self):
        if self.files_completeness not in {"complete", "truncated", "unknown"}:
            raise ValueError("Invalid changed-file completeness state.")


@dataclass(frozen=True, slots=True)
class CommitDiffProviderPage:
    files: tuple[CommitDiffFile, ...]
    files_completeness: FilesCompleteness


@dataclass(frozen=True, slots=True)
class BoundedCommitDiff:
    files: tuple[CommitDiffFile, ...]
    files_completeness: FilesCompleteness
    total_diff_bytes: int


@dataclass(frozen=True, slots=True)
class CommitDiffDetails:
    finding_id: UUID
    repository_name: str
    repository_name_truncated: bool
    repository_full_path: str
    repository_full_path_truncated: bool
    commit_hash: str
    author_name: str | None
    author_email: str | None
    authored_at: datetime | None
    commit_message_summary: str | None
    files: tuple[CommitDiffFile, ...]
    files_completeness: FilesCompleteness
    total_diff_bytes: int


def normalize_commit_diff(files, files_completeness: FilesCompleteness, *, max_files=MAX_DIFF_FILES,
                          max_file_bytes=MAX_DIFF_BYTES_PER_FILE,
                          max_total_bytes=MAX_TOTAL_DIFF_BYTES,
                          max_path_bytes=MAX_DIFF_PATH_BYTES) -> BoundedCommitDiff:
    if files_completeness not in {"complete", "truncated", "unknown"}:
        raise ValueError("Invalid changed-file completeness state.")
    if not 1 <= max_files <= MAX_DIFF_FILES or not 1 <= max_file_bytes <= MAX_DIFF_BYTES_PER_FILE:
        raise ValueError("Commit diff limits exceed supported bounds.")
    if not 1 <= max_total_bytes <= MAX_TOTAL_DIFF_BYTES or not 1 <= max_path_bytes <= MAX_DIFF_PATH_BYTES:
        raise ValueError("Commit diff limits exceed supported bounds.")

    incoming = tuple(files)
    completeness = "truncated" if files_completeness == "truncated" or len(incoming) > max_files else files_completeness
    output = []
    total = 0
    total_exhausted = False
    for item in incoming[:max_files]:
        old_path, old_clipped = bound_utf8(item.old_path, max_path_bytes)
        new_path, new_clipped = bound_utf8(item.new_path, max_path_bytes)
        diff = item.diff
        diff_clipped = item.diff_truncated
        if diff is not None:
            diff, per_file_clipped = bound_utf8(diff, max_file_bytes)
            diff_clipped = diff_clipped or per_file_clipped
            if total_exhausted:
                diff, diff_clipped = None, True
            else:
                available = max_total_bytes - total
                encoded = diff.encode("utf-8")
                if len(encoded) > available:
                    diff, _ = bound_utf8(diff, available)
                    diff = diff or None
                    total_exhausted = True
                    diff_clipped = True
                total += len((diff or "").encode("utf-8"))
        output.append(replace(item, old_path=old_path, new_path=new_path, diff=diff,
                              text_diff_available=bool(diff), diff_truncated=diff_clipped,
                              old_path_truncated=item.old_path_truncated or old_clipped,
                              new_path_truncated=item.new_path_truncated or new_clipped))
    return BoundedCommitDiff(tuple(output), completeness, total)
