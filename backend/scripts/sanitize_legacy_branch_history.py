"""Opt-in, configuration-scoped deletion of obsolete default-branch history.

This is for disposable development/test execution history only. It never deletes
Monitoring Configurations, GitLab credentials, scope, target/author policies, or schedules.
"""
import argparse
import os
from uuid import UUID

from sqlalchemy import create_engine, text


def sanitize(engine, configuration_id: UUID) -> dict[str, int]:
    counts = {}
    with engine.begin() as connection:
        counts["findings"] = connection.execute(text("""
            DELETE FROM findings f USING repository_executions r, mining_executions e
            WHERE f.repository_execution_id = r.id
              AND r.mining_execution_id = e.id
              AND e.monitoring_configuration_id = :configuration_id
        """), {"configuration_id": configuration_id}).rowcount
        counts["repository_executions"] = connection.execute(text("""
            DELETE FROM repository_executions r USING mining_executions e
            WHERE r.mining_execution_id = e.id
              AND e.monitoring_configuration_id = :configuration_id
        """), {"configuration_id": configuration_id}).rowcount
        counts["mining_executions"] = connection.execute(text("""
            DELETE FROM mining_executions WHERE monitoring_configuration_id = :configuration_id
        """), {"configuration_id": configuration_id}).rowcount
        counts["repository_checkpoints"] = connection.execute(text("""
            DELETE FROM repository_checkpoints WHERE monitoring_configuration_id = :configuration_id
        """), {"configuration_id": configuration_id}).rowcount
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--configuration-id", required=True, type=UUID)
    parser.add_argument("--confirm", action="store_true", help="Confirm deletion of this configuration's mining history")
    args = parser.parse_args()
    environment = os.getenv("APP_ENV", "").casefold()
    if environment not in {"development", "dev", "test", "local"}:
        parser.error("APP_ENV must identify a development/test/local environment.")
    if os.getenv("ALLOW_DEVELOPMENT_HISTORY_CLEANUP") != "1":
        parser.error("Set ALLOW_DEVELOPMENT_HISTORY_CLEANUP=1 to explicitly enable this command.")
    if not args.confirm:
        parser.error("Pass --confirm after verifying the selected Monitoring Configuration ID.")
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        parser.error("DATABASE_URL is required.")
    engine = create_engine(database_url)
    try:
        result = sanitize(engine, args.configuration_id)
    finally:
        engine.dispose()
    print("Deleted rows for the selected configuration: " + ", ".join(f"{key}={value}" for key, value in result.items()))


if __name__ == "__main__":
    main()
