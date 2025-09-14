import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud
from app.api import deps
from app.core.db_utils import PaginationParams
from app.models.user import User, UserRole

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/dashboard", response_model=Dict)  # type: ignore[misc]
async def get_analytics_dashboard(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.require_role(UserRole.ADMIN)),
) -> Dict:
    """
    Get comprehensive dashboard analytics with all key metrics.
    """
    # Log admin access for audit trail
    logger.info(
        f"Analytics dashboard accessed by admin user {current_user.id} ({current_user.email})"
    )
    return await crud.analytics.get_dashboard_metrics(db)


@router.get("/statistics", response_model=Dict)  # type: ignore[misc]
async def get_booking_statistics(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.require_role(UserRole.ADMIN)),
    period_days: int = Query(30, ge=1, le=365, description="Analysis period in days"),
) -> Dict:
    """
    Get comprehensive booking statistics including revenue, cancellation rate, etc.
    """
    return await crud.analytics.get_booking_statistics(db, period_days)


@router.get("/popular-events", response_model=List[Dict])  # type: ignore[misc]
async def get_popular_events(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.require_role(UserRole.ADMIN)),
    limit: int = Query(10, ge=1, le=50, description="Number of events to return"),
    period_days: Optional[int] = Query(
        None, ge=1, le=365, description="Period in days"
    ),
) -> List[Dict]:
    """
    Get most popular events by booking count with detailed metrics.
    """
    results = await crud.analytics.get_popular_events(db, limit, period_days)
    return [
        {
            "event": {
                "id": row.Event.id,
                "name": row.Event.name,
                "start_date": row.Event.start_date,
                "location": row.Event.location,
                "price": float(row.Event.price),
                "capacity": row.Event.capacity,
            },
            "booking_count": row.booking_count,
            "total_tickets_sold": row.total_tickets_sold,
            "total_revenue": float(row.total_revenue or 0),
            "avg_revenue_per_booking": float(row.avg_revenue_per_booking or 0),
            "conversion_rate": round(float(row.conversion_rate or 0), 2),
        }
        for row in results
    ]


@router.get("/trends", response_model=Dict)  # type: ignore[misc]
async def get_booking_trends(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.require_role(UserRole.ADMIN)),
    period: str = Query("daily", regex="^(daily|weekly|monthly)$"),
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
) -> Dict:
    """
    Get booking trends with various time granularities.
    """
    return await crud.analytics.get_booking_trends(db, period, days)


@router.get("/revenue-analysis", response_model=Dict)  # type: ignore[misc]
async def get_revenue_analysis(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.require_role(UserRole.ADMIN)),
    period_days: int = Query(30, ge=1, le=365),
) -> Dict:
    """
    Get comprehensive revenue analysis with breakdowns and comparisons.
    """
    return await crud.analytics.get_revenue_analysis(db, period_days)


@router.get("/capacity-utilization", response_model=Dict[str, Any])  # type: ignore[misc]
async def get_capacity_utilization(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.require_role(UserRole.ADMIN)),
    pagination: PaginationParams = Depends(),
    min_utilization: Optional[float] = Query(None, ge=0, le=100),
) -> dict[str, Any]:
    """
    Get capacity utilization metrics for events with filtering.
    """
    return await crud.analytics.get_capacity_utilization(
        db, pagination, min_utilization
    )


@router.get("/user-behavior", response_model=Dict)  # type: ignore[misc]
async def get_user_behavior_analysis(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.require_role(UserRole.ADMIN)),
    period_days: int = Query(30, ge=1, le=365),
) -> Dict:
    """
    Get comprehensive user behavior analysis including segmentation.
    """
    return await crud.analytics.get_user_behavior_analysis(db, period_days)


@router.get("/cohort-analysis", response_model=Dict)  # type: ignore[misc]
async def get_cohort_analysis(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.require_role(UserRole.ADMIN)),
    months: int = Query(6, ge=1, le=24, description="Number of months to analyze"),
) -> Dict:
    """
    Get user cohort analysis showing retention patterns.
    """
    return await crud.analytics.get_cohort_analysis(db, months)


@router.get("/waitlist-analytics", response_model=Dict)  # type: ignore[misc]
async def get_waitlist_analytics(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.require_role(UserRole.ADMIN)),
    period_days: int = Query(30, ge=1, le=365),
) -> Dict:
    """
    Get comprehensive waitlist analytics including conversion rates.
    """
    return await crud.analytics.get_waitlist_analytics(db, period_days)


@router.get("/event-performance/{event_id}", response_model=Dict)  # type: ignore[misc]
async def get_event_performance(
    event_id: int,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.require_role(UserRole.ADMIN)),
) -> Dict:
    """
    Get detailed performance metrics for a specific event.
    """
    return await crud.analytics.get_event_performance(db, event_id)


@router.get("/geographical-analysis", response_model=Dict)  # type: ignore[misc]
async def get_geographical_analysis(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.require_role(UserRole.ADMIN)),
    period_days: int = Query(30, ge=1, le=365),
) -> Dict:
    """
    Get geographical distribution of events and bookings.
    """
    return await crud.analytics.get_geographical_analysis(db, period_days)


@router.get("/forecasting", response_model=Dict)  # type: ignore[misc]
async def get_demand_forecasting(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.require_role(UserRole.ADMIN)),
    forecast_days: int = Query(30, ge=7, le=90),
) -> Dict:
    """
    Get demand forecasting based on historical data.
    """
    return await crud.analytics.get_demand_forecasting(db, forecast_days)


@router.get("/real-time-metrics", response_model=Dict)  # type: ignore[misc]
async def get_real_time_metrics(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.require_role(UserRole.ADMIN)),
) -> Dict:
    """
    Get real-time metrics for monitoring dashboard.
    """
    return await crud.analytics.get_real_time_metrics(db)
