from functools import lru_cache
import math

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    cors_origins: str
    scheduler_enabled: bool = True
    schedule_poll_interval_seconds: int = 10
    scheduled_execution_concurrency: int = 4
    gitlab_credential_encryption_keys: str = ""
    gitlab_connect_timeout_seconds: float = 5
    gitlab_read_timeout_seconds: float = 10
    gitlab_write_timeout_seconds: float = 5
    gitlab_pool_timeout_seconds: float = 5
    execution_staleness_threshold_seconds: float = 300
    repository_mining_concurrency: int = 4
    repository_mining_max_tree_entries: int = 50_000
    repository_mining_max_file_bytes: int = 1_048_576
    repository_mining_max_extensions: int = 100
    mining_max_commits_per_repository_execution: int = 1000
    finding_diff_max_files: int = 100
    finding_diff_max_file_bytes: int = 262144
    finding_diff_max_total_bytes: int = 2097152
    finding_diff_max_path_bytes: int = 4096
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("schedule_poll_interval_seconds")
    @classmethod
    def bounded_schedule_poll_interval(cls, value: int) -> int:
        if type(value) is not int or not 1 <= value <= 60:
            raise ValueError("Schedule poll interval must be between 1 and 60 seconds.")
        return value

    @field_validator("scheduled_execution_concurrency")
    @classmethod
    def bounded_scheduled_execution_concurrency(cls, value: int) -> int:
        if type(value) is not int or not 1 <= value <= 8:
            raise ValueError("Scheduled execution concurrency must be between 1 and 8.")
        return value

    @field_validator('execution_staleness_threshold_seconds')
    @classmethod
    def positive_finite_staleness(cls, value: float) -> float:
        if not math.isfinite(value) or value <= 0:
            raise ValueError('Execution staleness threshold must be finite and greater than zero.')
        return value

    @field_validator(
        "gitlab_connect_timeout_seconds", "gitlab_read_timeout_seconds",
        "gitlab_write_timeout_seconds", "gitlab_pool_timeout_seconds",
    )
    @classmethod
    def positive_finite_timeout(cls, value: float) -> float:
        if not math.isfinite(value) or value <= 0:
            raise ValueError("GitLab HTTP timeouts must be finite and greater than zero.")
        return value

    @field_validator("repository_mining_concurrency")
    @classmethod
    def bounded_repository_concurrency(cls, value: int) -> int:
        if type(value) is not int or not 1 <= value <= 8:
            raise ValueError("Repository mining concurrency must be between 1 and 8.")
        return value

    @field_validator("repository_mining_max_tree_entries", "repository_mining_max_file_bytes")
    @classmethod
    def positive_mining_limits(cls, value: int) -> int:
        if type(value) is not int or value < 1:
            raise ValueError("Repository mining limits must be positive integers.")
        return value

    @field_validator("repository_mining_max_extensions")
    @classmethod
    def bounded_mining_extensions(cls, value: int) -> int:
        if type(value) is not int or not 1 <= value <= 100:
            raise ValueError("Repository mining maximum extensions must be between 1 and 100.")
        return value

    @field_validator("mining_max_commits_per_repository_execution")
    @classmethod
    def bounded_commit_processing_limit(cls, value: int) -> int:
        if type(value) is not int or not 1 <= value <= 10_000:
            raise ValueError("Maximum commits per repository execution must be between 1 and 10000.")
        return value

    @field_validator("finding_diff_max_files")
    @classmethod
    def bounded_finding_diff_files(cls, value: int) -> int:
        if type(value) is not int or not 1 <= value <= 100:
            raise ValueError("Finding diff file limit must be between 1 and 100.")
        return value

    @field_validator("finding_diff_max_file_bytes")
    @classmethod
    def bounded_finding_diff_file_bytes(cls, value: int) -> int:
        if type(value) is not int or not 1 <= value <= 262144:
            raise ValueError("Finding diff per-file limit must be between 1 and 262144 bytes.")
        return value

    @field_validator("finding_diff_max_total_bytes")
    @classmethod
    def bounded_finding_diff_total_bytes(cls, value: int) -> int:
        if type(value) is not int or not 1 <= value <= 2097152:
            raise ValueError("Finding diff total limit must be between 1 and 2097152 bytes.")
        return value

    @field_validator("finding_diff_max_path_bytes")
    @classmethod
    def bounded_finding_diff_path_bytes(cls, value: int) -> int:
        if type(value) is not int or not 1 <= value <= 4096:
            raise ValueError("Finding diff path limit must be between 1 and 4096 bytes.")
        return value

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def gitlab_encryption_key_ring(self) -> list[str]:
        return [item.strip() for item in self.gitlab_credential_encryption_keys.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
