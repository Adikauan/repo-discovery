import json
import os
from uuid import uuid4

from alembic import command
from alembic.config import Config
import sqlalchemy as sa
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

from app.config import get_settings
from tests.unit.test_mining_execution import NOW


def test_0011_removes_obsolete_scope_rules_and_preserves_configuration_and_history(test_database_url):
    os.environ["DATABASE_URL"] = test_database_url
    get_settings.cache_clear()
    alembic = Config("alembic.ini")
    engine = create_engine(test_database_url, poolclass=NullPool)
    configuration_id, execution_id, repository_execution_id = uuid4(), uuid4(), uuid4()
    checkpoint_id, policy_id = uuid4(), uuid4()
    fingerprint = "a" * 64
    try:
        command.downgrade(alembic, "base")
        command.upgrade(alembic, "0009_author_policies")
        with engine.begin() as connection:
            connection.execute(text("""
                INSERT INTO monitoring_configurations
                  (id,name,description,gitlab_url,enabled,created_at,updated_at,revision,allowed_author_emails,author_policy_mode)
                VALUES (:id,'migration fixture',NULL,'https://gitlab.example',false,:now,:now,1,'[]'::jsonb,'scope_aware')
            """), {"id": configuration_id, "now": NOW})
            connection.execute(text("""
                INSERT INTO gitlab_credentials
                  (monitoring_configuration_id,encrypted_token,credential_revision,created_at,updated_at)
                VALUES (:id,:token,1,:now,:now)
            """), {"id": configuration_id, "token": b"encrypted-test-credential", "now": NOW})
            connection.execute(text("INSERT INTO monitoring_configuration_scopes (configuration_id,version,updated_at) VALUES (:id,1,:now)"),
                               {"id": configuration_id, "now": NOW})
            connection.execute(text("""
                INSERT INTO selected_gitlab_groups (selection_id,configuration_id,instance_fingerprint,gitlab_group_id,name,full_path,parent_group_id,updated_at)
                VALUES (:selection,:id,:fingerprint,31,'Backend','acme/backend',NULL,:now)
            """), {"selection": uuid4(), "id": configuration_id, "fingerprint": fingerprint, "now": NOW})
            connection.execute(text("""
                INSERT INTO selected_gitlab_repositories (selection_id,configuration_id,instance_fingerprint,gitlab_project_id,name,full_path,parent_group_id,updated_at)
                VALUES (:selection,:id,:fingerprint,42,'API','acme/backend/api',31,:now)
            """), {"selection": uuid4(), "id": configuration_id, "fingerprint": fingerprint, "now": NOW})
            connection.execute(text("""
                INSERT INTO monitoring_schedules (monitoring_configuration_id,configured,version,updated_at)
                VALUES (:id,false,1,:now)
            """), {"id": configuration_id, "now": NOW})
            connection.execute(text("""
                INSERT INTO author_policies (id,monitoring_configuration_id,scope_type,instance_fingerprint,full_path,gitlab_group_id)
                VALUES (:policy,:id,'group',:fingerprint,'acme/backend',31)
            """), {"policy": policy_id, "id": configuration_id, "fingerprint": fingerprint})
            connection.execute(text("""
                INSERT INTO author_policy_authors (policy_id,normalized_email,display_email)
                VALUES (:policy,'allowed@example.com','Allowed@example.com')
            """), {"policy": policy_id})
            connection.execute(text("""
                INSERT INTO mining_executions (id,monitoring_configuration_id,trigger_type,status,created_at,started_at,completed_at,snapshot)
                VALUES (:id,:configuration,'manual','completed',:now,:now,:now,CAST(:snapshot AS jsonb))
            """), {"id": execution_id, "configuration": configuration_id, "now": NOW,
                    "snapshot": json.dumps({"schema_version": 2, "configuration_id": str(configuration_id)})})
            connection.execute(text("""
                INSERT INTO repository_executions
                  (id,mining_execution_id,gitlab_project_id,repository_name,repository_full_path,status,started_at,completed_at,processed_branch)
                VALUES (:id,:execution,42,'API','acme/backend/api','completed',:now,:now,'master')
            """), {"id": repository_execution_id, "execution": execution_id, "now": NOW})
            connection.execute(text("""
                INSERT INTO findings
                  (id,repository_execution_id,rule_id,rule_version,severity,title,summary,commit_hash,author_email,author_email_state,created_at)
                VALUES (:id,:repository,'unauthorized_commit_author','1','warning','Unauthorized author','Historical finding',:hash,'bad@example.com','valid',:now)
            """), {"id": uuid4(), "repository": repository_execution_id, "hash": "b" * 40, "now": NOW})
            connection.execute(text("""
                INSERT INTO repository_checkpoints
                  (id,monitoring_configuration_id,gitlab_project_id,branch,last_successful_commit_hash,updated_at)
                VALUES (:checkpoint,:configuration,42,'master',:hash,:now)
            """), {"checkpoint": checkpoint_id, "configuration": configuration_id, "hash": "c" * 40, "now": NOW})

        command.upgrade(alembic, "0010_repository_target_branches")
        with engine.begin() as connection:
            connection.execute(text("""
                INSERT INTO target_branch_rules
                  (id,monitoring_configuration_id,scope_type,instance_fingerprint,gitlab_scope_id,full_path,branch_name,updated_at)
                VALUES (:rule,:id,'repository',:fingerprint,42,'acme/backend/api','quality',:now)
            """), {"rule": uuid4(), "id": configuration_id, "fingerprint": fingerprint, "now": NOW})
        command.upgrade(alembic, "head")
        with engine.connect() as connection:
            assert "target_branch_rules" not in set(sa.inspect(connection).get_table_names())
            assert connection.scalar(text("SELECT count(*) FROM repository_checkpoints")) == 0
            for table in ("monitoring_configurations", "gitlab_credentials", "monitoring_configuration_scopes",
                          "selected_gitlab_groups", "selected_gitlab_repositories", "monitoring_schedules",
                          "author_policies", "author_policy_authors", "mining_executions",
                          "repository_executions", "findings"):
                assert connection.scalar(text(f"SELECT count(*) FROM {table}")) == 1
            assert connection.scalar(text("SELECT target_branch FROM repository_executions WHERE id=:id"),
                                     {"id": repository_execution_id}) is None
            assert connection.scalar(text("SELECT branch FROM repository_checkpoints WHERE id=:id"),
                                     {"id": checkpoint_id}) is None
    finally:
        command.downgrade(alembic, "base")
        engine.dispose()
        get_settings.cache_clear()
