"""Task management routes."""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import User, Task, Project, UserRole
from app.schemas.task import TaskCreate, TaskUpdate, TaskOut
from app.schemas.common import APIResponse
from app.api.deps import get_current_user, require_admin_role

logger = logging.getLogger("app.tasks")

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.post("/", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
def create_task(
    payload: TaskCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin_role),
):
    """Create a new task (Admin only)."""
    # Validate project exists
    project = db.query(Project).filter(Project.id == payload.project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project not found",
        )

    # Validate assignee if provided
    if payload.assigned_to_id:
        assignee = db.query(User).filter(User.id == payload.assigned_to_id).first()
        if not assignee:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Assigned user not found",
            )

    task = Task(
        title=payload.title,
        description=payload.description,
        project_id=payload.project_id,
        assigned_to_id=payload.assigned_to_id,
        priority=payload.priority,
        due_date=payload.due_date,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    logger.info("Task created: '%s' in project '%s' by %s", task.title, project.name, admin.username)

    return APIResponse(
        success=True,
        message="Task created successfully",
        data=TaskOut.model_validate(task).model_dump(),
    )


@router.get("/", response_model=APIResponse)
def list_tasks(
    project_id: str | None = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List tasks. Optionally filter by project_id query param. Supports pagination."""
    query = db.query(Task)
    if project_id:
        query = query.filter(Task.project_id == project_id)
    tasks = query.offset(skip).limit(limit).all()
    return APIResponse(
        success=True,
        message="Tasks retrieved",
        data=[TaskOut.model_validate(t).model_dump() for t in tasks],
    )


@router.get("/{task_id}", response_model=APIResponse)
def get_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single task by ID."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )
    return APIResponse(
        success=True,
        message="Task retrieved",
        data=TaskOut.model_validate(task).model_dump(),
    )


@router.patch("/{task_id}", response_model=APIResponse)
def update_task(
    task_id: str,
    payload: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update a task.
    - Admin can update any task field.
    - Members can only update tasks assigned to them (status only).
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    # RBAC check
    if current_user.role != UserRole.ADMIN:
        # Members can only update tasks assigned to them
        if task.assigned_to_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only update tasks assigned to you",
            )
        # Members can only change status
        update_data = payload.model_dump(exclude_unset=True)
        member_allowed = {"status"}
        non_status_fields = {k for k in update_data if k not in member_allowed}
        if non_status_fields:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Members can only update the task status",
            )

    # Validate assignee if provided
    if payload.assigned_to_id is not None:
        assignee = db.query(User).filter(User.id == payload.assigned_to_id).first()
        if not assignee:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Assigned user not found",
            )

    # Apply updates
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)

    task.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(task)

    logger.info("Task updated: '%s' by %s", task.title, current_user.username)

    return APIResponse(
        success=True,
        message="Task updated successfully",
        data=TaskOut.model_validate(task).model_dump(),
    )
