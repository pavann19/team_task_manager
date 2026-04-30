"""Task-related Pydantic schemas."""

from datetime import datetime, timezone, timedelta
from typing import Optional
from pydantic import BaseModel, Field, model_validator

from app.db.models import TaskStatus, TaskPriority


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = ""
    project_id: str = Field(..., min_length=1)
    assigned_to_id: Optional[str] = None
    priority: Optional[TaskPriority] = None
    due_date: datetime = Field(...)

    @model_validator(mode='after')
    def auto_priority(self) -> 'TaskCreate':
        """Auto-assign priority based on due_date if not manually set."""
        if self.priority is None and self.due_date:
            now = datetime.now(timezone.utc)
            due = self.due_date if self.due_date.tzinfo else self.due_date.replace(tzinfo=timezone.utc)
            days_left = (due - now).days
            if days_left <= 2:
                self.priority = TaskPriority.HIGH
            elif days_left <= 5:
                self.priority = TaskPriority.MEDIUM
            else:
                self.priority = TaskPriority.LOW
        elif self.priority is None:
            self.priority = TaskPriority.MEDIUM
        return self


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    assigned_to_id: Optional[str] = None
    priority: Optional[TaskPriority] = None
    due_date: Optional[datetime] = None


class TaskOut(BaseModel):
    id: str
    title: str
    description: Optional[str]
    status: TaskStatus
    priority: TaskPriority
    due_date: Optional[datetime]
    project_id: str
    assigned_to_id: Optional[str]
    assigned_to_username: Optional[str] = None
    is_overdue: bool = False
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}
