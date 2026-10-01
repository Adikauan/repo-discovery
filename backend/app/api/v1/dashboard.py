from fastapi import APIRouter, Depends
from app.api.dependencies import get_uow
from app.api.v1.dashboard_schemas import DashboardSummaryResponse
from app.application.use_cases.get_dashboard_summary import GetDashboardSummary

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummaryResponse)
def dashboard_summary(uow=Depends(get_uow)):
    return GetDashboardSummary(uow).execute()
