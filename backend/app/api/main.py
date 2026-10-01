from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError

from app.api.errors import domain_error_handler, request_validation_error_handler
from app.api.v1.gitlab_connections import router as gitlab_connections_router, candidate_router as gitlab_candidate_router
from app.api.v1.gitlab_scopes import router as gitlab_scopes_router
from app.api.v1.monitoring_schedules import router as monitoring_schedules_router
from app.api.v1.executions import router as executions_router
from app.api.v1.repository_executions import router as repository_executions_router
from app.api.v1.findings import router as findings_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.monitoring_configurations import router
from app.api.v1.author_policies import router as author_policies_router
from app.config import get_settings
from app.domain.errors import (BadRequestError, ConflictError, FieldValidationError, MissingPreconditionError,
                               NotFoundError, CredentialServiceUnavailable, CommitDiffError, AuthorPolicyApiError)


def create_app(*, scheduler_enabled: bool | None = None, scheduler_runner_factory=None) -> FastAPI:
    settings = get_settings()
    enabled = settings.scheduler_enabled if scheduler_enabled is None else scheduler_enabled
    runner_factory = scheduler_runner_factory

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        runner = None
        if enabled:
            if app.state.scheduler_runner is None:
                factory = runner_factory
                if factory is None:
                    from app.api.scheduler_runtime import create_scheduler_runner
                    factory = create_scheduler_runner
                app.state.scheduler_runner = factory()
            runner = app.state.scheduler_runner
            await runner.start()
        try:
            yield
        finally:
            if runner is not None:
                await runner.stop()

    app = FastAPI(title="Repository Mining API", version="1.0.0", lifespan=lifespan)
    app.state.scheduler_runner = None
    app.add_middleware(CORSMiddleware, allow_origins=settings.allowed_origins,
                       allow_credentials=False, allow_methods=["GET", "POST", "PUT", "DELETE"],
                       allow_headers=["Content-Type", "Idempotency-Key", "If-Match"],
                       expose_headers=["ETag", "Location"])
    app.add_exception_handler(RequestValidationError, request_validation_error_handler)
    for error in (BadRequestError, FieldValidationError, NotFoundError, ConflictError,
                  MissingPreconditionError, CredentialServiceUnavailable, CommitDiffError, AuthorPolicyApiError):
        app.add_exception_handler(error, domain_error_handler)
    app.add_exception_handler(Exception, domain_error_handler)
    app.include_router(router, prefix="/api/v1")
    app.include_router(gitlab_connections_router, prefix="/api/v1")
    app.include_router(gitlab_candidate_router, prefix="/api/v1")
    app.include_router(gitlab_scopes_router, prefix="/api/v1")
    app.include_router(monitoring_schedules_router, prefix="/api/v1")
    app.include_router(executions_router, prefix="/api/v1")
    app.include_router(repository_executions_router, prefix="/api/v1")
    app.include_router(findings_router, prefix="/api/v1")
    app.include_router(dashboard_router, prefix="/api/v1")
    app.include_router(author_policies_router, prefix="/api/v1")
    @app.get("/health")
    def health(): return {"status": "ok"}
    return app


app = create_app()
