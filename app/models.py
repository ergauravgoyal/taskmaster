from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, EmailStr, Field

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(min_length=1, max_length=120)

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: EmailStr
    name: str
    created_at: datetime

class ProfileUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=120)

class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    description: str | None = None

class ProjectResponse(ProjectCreate):
    id: int
    owner_id: int
    created_at: datetime

class MemberAdd(BaseModel):
    user_id: int

class InvitationResponse(BaseModel):
    id: int
    project_id: int
    inviter_id: int
    invitee_id: int
    status: str
    created_at: datetime
    responded_at: datetime | None

class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    due_date: datetime | None = None
    assignee_id: int | None = None

class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    due_date: datetime | None = None
    status: str | None = Field(default=None, pattern="^(open|in_progress|completed)$")
    assignee_id: int | None = None

class TaskResponse(BaseModel):
    id: int
    project_id: int
    title: str
    description: str | None
    due_date: datetime | None
    status: str
    assignee_id: int | None
    creator_id: int
    created_at: datetime
    updated_at: datetime

class CommentCreate(BaseModel):
    body: str = Field(min_length=1, max_length=5000)

class CommentResponse(BaseModel):
    id: int
    task_id: int
    author_id: int
    body: str
    created_at: datetime

class AttachmentCreate(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=1, max_length=120)
    storage_key: str = Field(min_length=1, max_length=500)
    size_bytes: int = Field(ge=0)

class AttachmentResponse(AttachmentCreate):
    id: int
    task_id: int
    uploader_id: int
    created_at: datetime

class AssignedTaskResponse(TaskResponse):
    project_name: str
