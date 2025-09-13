from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud
from app.api import deps
from app.models.user import User

router = APIRouter()


@router.get("/statistics", response_model=Dict)
async def get_booking_statistics(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    Get comprehensive booking statistics including revenue, cancellation rate, etc.
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return await crud.analytics.get_booking_statistics(db)


@router.get("/popular-events", response_model=List[Dict])
async def get_popular_events(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    limit: int = Query(10, ge=1, le=50, description="Number of events to return"),
):
    """
    Get most popular events by booking count with detailed metrics.
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    results = await crud.analytics.get_popular_events(db, limit)
    return [
        {
            "event": row.Event,
            "booking_count": row.booking_count,
            "total_tickets_sold": row.total_tickets_sold,
            "avg_revenue_per_booking": float(row.avg_revenue_per_booking or 0),
        }
        for row in results
    ]


@router.get("/daily-stats", response_model=List[Dict])
async def get_daily_booking_stats(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
):
    """
    Get daily booking statistics for the specified period.
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return await crud.analytics.get_daily_booking_stats(db, days)


@router.get("/capacity-utilization", response_model=List[Dict])
async def get_capacity_utilization(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    Get capacity utilization metrics for all events.
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return await crud.analytics.get_capacity_utilization(db)


@router.get("/revenue-by-event", response_model=List[Dict])
async def get_revenue_by_event(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    limit: int = Query(10, ge=1, le=50, description="Number of events to return"),
):
    """
    Get top revenue generating events.
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return await crud.analytics.get_revenue_by_event(db, limit)


@router.get("/user-engagement", response_model=Dict)
async def get_user_engagement_stats(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    Get user engagement statistics including active users and repeat customers.
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return await crud.analytics.get_user_engagement_stats(db)


@router.get("/waitlist-analytics", response_model=Dict)
async def get_waitlist_analytics(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    Get waitlist analytics including conversion rates.
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return await crud.analytics.get_waitlist_analytics(db)
