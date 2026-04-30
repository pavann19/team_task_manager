"""Project management routes."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import User, Project
from app.schemas.project import ProjectCreate, ProjectOut
from app.schemas.common import APIResponse
from app.api.deps import get_current_user, require_admin_role

logger = logging.getLogger("app.projects")

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.post("/", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin_role),
):
    """Create a new project (Admin only)."""
    project = Project(
        name=payload.name,
        description=payload.description,
        owner_id=admin.id,
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    logger.info("Project created: '%s' by %s", project.name, admin.username)

    return APIResponse(
        success=True,
        message="Project created successfully",
        data=ProjectOut.model_validate(project).model_dump(),
    )


@router.get("/", response_model=APIResponse)
def list_projects(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all projects with pagination."""
    projects = db.query(Project).offset(skip).limit(limit).all()
    return APIResponse(
        success=True,
        message="Projects retrieved",
        data=[ProjectOut.model_validate(p).model_dump() for p in projects],
    )


@router.get("/{project_id}", response_model=APIResponse)
def get_project(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single project by ID."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    return APIResponse(
        success=True,
        message="Project retrieved",
        data=ProjectOut.model_validate(project).model_dump(),
    )
