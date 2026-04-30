"""Analytics endpoint – Admin-only aggregation dashboard."""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import Task, Project, TaskStatus
from app.schemas.common import APIResponse
from app.api.deps import require_admin_role
from app.db.models import User

logger = logging.getLogger("app.analytics")

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/", response_model=APIResponse)
def get_analytics(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin_role),
):
    """
    Return aggregated metrics (Admin only).

    - total_projects
    - total_tasks
    - tasks_by_status  → counts grouped by status
    - overdue_tasks    → due_date < now AND status != Completed
    """
    now = datetime.now(timezone.utc)

    total_projects: int = db.query(func.count(Project.id)).scalar() or 0
    total_tasks: int = db.query(func.count(Task.id)).scalar() or 0

    # Group-by status counts
    status_rows = (
        db.query(Task.status, func.count(Task.id))
        .group_by(Task.status)
        .all()
    )
    tasks_by_status = {
        TaskStatus.PENDING.value: 0,
        TaskStatus.IN_PROGRESS.value: 0,
        TaskStatus.COMPLETED.value: 0,
    }
    for status, count in status_rows:
        tasks_by_status[status.value] = count

    # Overdue: due_date set, past now, not completed
    overdue_tasks: int = (
        db.query(func.count(Task.id))
        .filter(
            Task.due_date.isnot(None),
            Task.due_date < now,
            Task.status != TaskStatus.COMPLETED,
        )
        .scalar()
        or 0
    )

    logger.info("Analytics fetched by admin")

    return APIResponse(
        success=True,
        message="Analytics data fetched",
        data={
            "total_tasks": total_tasks,
            "completed_tasks": tasks_by_status.get(TaskStatus.COMPLETED.value, 0),
            "pending_tasks": tasks_by_status.get(TaskStatus.PENDING.value, 0),
            "in_progress_tasks": tasks_by_status.get(TaskStatus.IN_PROGRESS.value, 0),
            "overdue_tasks": overdue_tasks,
        },
    )
