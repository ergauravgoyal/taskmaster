from pathlib import Path
from uuid import uuid4
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from app.config import settings
from app.db import connection
from app.deps import current_user
from app.models import (
    AttachmentCreate, AttachmentResponse, CommentCreate, CommentResponse,
    TaskCreate, TaskResponse, TaskUpdate,
)

router = APIRouter(prefix="/projects/{project_id}/tasks", tags=["Tasks"])
assigned_router = APIRouter(prefix="/tasks", tags=["Tasks"])

async def ensure_member(conn, project_id: int, user_id: int):
    if not await conn.fetchval(
        "SELECT 1 FROM project_members WHERE project_id=$1 AND user_id=$2",
        project_id, user_id,
    ):
        raise HTTPException(403, "Project membership required")

@router.post("", response_model=TaskResponse, status_code=201)
async def create_task(project_id: int, payload: TaskCreate, user=Depends(current_user)):
    user_id = user[0]
    async with connection() as conn:
        await ensure_member(conn, project_id, user_id)
        if payload.assignee_id:
            await ensure_member(conn, project_id, payload.assignee_id)
        row = await conn.fetchrow(
            """
            INSERT INTO tasks(project_id,title,description,due_date,assignee_id,creator_id)
            VALUES($1,$2,$3,$4,$5,$6)
            RETURNING id,project_id,title,description,due_date,status,assignee_id,creator_id,created_at,updated_at
            """,
            project_id, payload.title, payload.description, payload.due_date,
            payload.assignee_id, user_id,
        )
        return dict(row)

@router.get("", response_model=list[TaskResponse])
async def list_tasks(
    project_id: int,
    status_filter: str | None = Query(default=None, alias="status", pattern="^(open|in_progress|completed)$"),
    assignee_id: int | None = None,
    search: str | None = Query(default=None, min_length=1),
    user=Depends(current_user),
):
    async with connection() as conn:
        await ensure_member(conn, project_id, user[0])
        conditions = ["project_id=$1"]
        args: list[object] = [project_id]
        if status_filter:
            args.append(status_filter)
            conditions.append(f"status=${len(args)}")
        if assignee_id:
            args.append(assignee_id)
            conditions.append(f"assignee_id=${len(args)}")
        if search:
            args.append(search)
            conditions.append(f"to_tsvector('simple', title || ' ' || coalesce(description,'')) @@ plainto_tsquery('simple', ${len(args)})")
        query = "SELECT id,project_id,title,description,due_date,status,assignee_id,creator_id,created_at,updated_at FROM tasks WHERE " + " AND ".join(conditions) + " ORDER BY due_date NULLS LAST, created_at DESC"
        rows = await conn.fetch(query, *args)
        return [dict(row) for row in rows]

@assigned_router.get("/assigned-to-me", response_model=list[TaskResponse])
async def assigned_tasks(
    status_filter: str | None = Query(default=None, alias="status", pattern="^(open|in_progress|completed)$"),
    user=Depends(current_user),
):
    conditions = ["t.assignee_id=$1"]
    args: list[object] = [user[0]]
    if status_filter:
        args.append(status_filter)
        conditions.append(f"t.status=${len(args)}")
    async with connection() as conn:
        rows = await conn.fetch(
            """
            SELECT t.id,t.project_id,t.title,t.description,t.due_date,t.status,
                   t.assignee_id,t.creator_id,t.created_at,t.updated_at
            FROM tasks t JOIN project_members pm ON pm.project_id=t.project_id AND pm.user_id=$1
            WHERE """ + " AND ".join(conditions) + " ORDER BY t.due_date NULLS LAST, t.created_at DESC",
            *args,
        )
    return [dict(row) for row in rows]

@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(project_id: int, task_id: int, payload: TaskUpdate, user=Depends(current_user)):
    values = payload.model_dump(exclude_unset=True)
    if not values:
        raise HTTPException(400, "At least one field is required")
    async with connection() as conn:
        await ensure_member(conn, project_id, user[0])
        if "assignee_id" in values and values["assignee_id"]:
            await ensure_member(conn, project_id, values["assignee_id"])
        allowed = {"title", "description", "due_date", "status", "assignee_id"}
        assignments = []
        args: list[object] = [project_id, task_id]
        for field in allowed.intersection(values):
            args.append(values[field])
            assignments.append(f"{field}=${len(args)}")
        row = await conn.fetchrow(
            f"""
            UPDATE tasks SET {', '.join(assignments)}, updated_at=now()
            WHERE project_id=$1 AND id=$2
            RETURNING id,project_id,title,description,due_date,status,assignee_id,creator_id,created_at,updated_at
            """,
            *args,
        )
    if not row:
        raise HTTPException(404, "Task not found")
    return dict(row)

@router.delete("/{task_id}", status_code=204)
async def delete_task(project_id: int, task_id: int, user=Depends(current_user)):
    async with connection() as conn:
        await ensure_member(conn, project_id, user[0])
        result = await conn.execute("DELETE FROM tasks WHERE project_id=$1 AND id=$2", project_id, task_id)
    if result == "DELETE 0":
        raise HTTPException(404, "Task not found")

@router.post("/{task_id}/comments", response_model=CommentResponse, status_code=201)
async def add_comment(project_id: int, task_id: int, payload: CommentCreate, user=Depends(current_user)):
    async with connection() as conn:
        await ensure_member(conn, project_id, user[0])
        task = await conn.fetchval("SELECT 1 FROM tasks WHERE id=$1 AND project_id=$2", task_id, project_id)
        if not task:
            raise HTTPException(404, "Task not found")
        row = await conn.fetchrow(
            "INSERT INTO comments(task_id,author_id,body) VALUES($1,$2,$3) RETURNING id,task_id,author_id,body,created_at",
            task_id, user[0], payload.body,
        )
        return dict(row)

@router.get("/{task_id}/comments", response_model=list[CommentResponse])
async def list_comments(project_id: int, task_id: int, user=Depends(current_user)):
    async with connection() as conn:
        await ensure_member(conn, project_id, user[0])
        rows = await conn.fetch(
            "SELECT c.id,c.task_id,c.author_id,c.body,c.created_at FROM comments c JOIN tasks t ON t.id=c.task_id WHERE c.task_id=$1 AND t.project_id=$2 ORDER BY c.created_at",
            task_id, project_id,
        )
        return [dict(row) for row in rows]

@router.post("/{task_id}/attachments", response_model=AttachmentResponse, status_code=201)
async def add_attachment(project_id: int, task_id: int, payload: AttachmentCreate, user=Depends(current_user)):
    async with connection() as conn:
        await ensure_member(conn, project_id, user[0])
        task = await conn.fetchval("SELECT 1 FROM tasks WHERE id=$1 AND project_id=$2", task_id, project_id)
        if not task:
            raise HTTPException(404, "Task not found")
        row = await conn.fetchrow(
            """
            INSERT INTO attachments(task_id,uploader_id,filename,content_type,storage_key,size_bytes)
            VALUES($1,$2,$3,$4,$5,$6)
            RETURNING id,task_id,uploader_id,filename,content_type,storage_key,size_bytes,created_at
            """,
            task_id, user[0], payload.filename, payload.content_type,
            payload.storage_key, payload.size_bytes,
        )
        return dict(row)

@router.post("/{task_id}/attachments/upload", response_model=AttachmentResponse, status_code=201)
async def upload_attachment(
    project_id: int,
    task_id: int,
    file: UploadFile = File(...),
    user=Depends(current_user),
):
    async with connection() as conn:
        await ensure_member(conn, project_id, user[0])
        if not await conn.fetchval("SELECT 1 FROM tasks WHERE id=$1 AND project_id=$2", task_id, project_id):
            raise HTTPException(404, "Task not found")
    storage_dir = Path(settings.attachment_dir)
    storage_dir.mkdir(parents=True, exist_ok=True)
    storage_key = f"{uuid4().hex}_{Path(file.filename or 'attachment').name}"
    target = storage_dir / storage_key
    size = 0
    with target.open("wb") as output:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            output.write(chunk)
    async with connection() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO attachments(task_id,uploader_id,filename,content_type,storage_key,size_bytes)
            VALUES($1,$2,$3,$4,$5,$6)
            RETURNING id,task_id,uploader_id,filename,content_type,storage_key,size_bytes,created_at
            """,
            task_id, user[0], file.filename or "attachment",
            file.content_type or "application/octet-stream", storage_key, size,
        )
    return dict(row)

@router.get("/{task_id}/attachments/{attachment_id}/download")
async def download_attachment(project_id: int, task_id: int, attachment_id: int, user=Depends(current_user)):
    async with connection() as conn:
        await ensure_member(conn, project_id, user[0])
        row = await conn.fetchrow(
            "SELECT filename,content_type,storage_key FROM attachments WHERE id=$1 AND task_id=$2",
            attachment_id, task_id,
        )
    if not row:
        raise HTTPException(404, "Attachment not found")
    path = Path(settings.attachment_dir) / row["storage_key"]
    if not path.is_file():
        raise HTTPException(404, "Attachment content not found")
    return FileResponse(path, media_type=row["content_type"], filename=row["filename"])
