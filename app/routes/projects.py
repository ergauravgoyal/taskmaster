from fastapi import APIRouter, Depends, HTTPException
from app.db import connection
from app.deps import current_user
from app.models import InvitationResponse, MemberAdd, ProjectCreate, ProjectResponse

router = APIRouter(prefix="/projects", tags=["Projects"])

@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(payload: ProjectCreate, user=Depends(current_user)):
    user_id = user[0]
    async with connection() as conn:
        async with conn.transaction():
            project = await conn.fetchrow(
                "INSERT INTO projects(name,description,owner_id) VALUES($1,$2,$3) RETURNING id,name,description,owner_id,created_at",
                payload.name, payload.description, user_id,
            )
            await conn.execute(
                "INSERT INTO project_members(project_id,user_id,role) VALUES($1,$2,'owner')",
                project["id"], user_id,
            )
    return dict(project)

@router.post("/{project_id}/members", status_code=204)
async def add_member(project_id: int, payload: MemberAdd, user=Depends(current_user)):
    user_id = user[0]
    async with connection() as conn:
        owner = await conn.fetchval("SELECT 1 FROM projects WHERE id=$1 AND owner_id=$2", project_id, user_id)
        if not owner:
            raise HTTPException(403, "Only the project owner can add members")
        exists = await conn.fetchval("SELECT 1 FROM users WHERE id=$1", payload.user_id)
        if not exists:
            raise HTTPException(404, "User not found")
        await conn.execute(
            "INSERT INTO project_members(project_id,user_id,role) VALUES($1,$2,'member') ON CONFLICT DO NOTHING",
            project_id, payload.user_id,
        )

@router.post("/{project_id}/invitations", response_model=InvitationResponse, status_code=201)
async def invite_member(project_id: int, payload: MemberAdd, user=Depends(current_user)):
    user_id = user[0]
    async with connection() as conn:
        owner = await conn.fetchval("SELECT 1 FROM projects WHERE id=$1 AND owner_id=$2", project_id, user_id)
        if not owner:
            raise HTTPException(403, "Only the project owner can invite members")
        if not await conn.fetchval("SELECT 1 FROM users WHERE id=$1", payload.user_id):
            raise HTTPException(404, "User not found")
        row = await conn.fetchrow(
            """
            INSERT INTO project_invitations(project_id,inviter_id,invitee_id)
            VALUES($1,$2,$3)
            ON CONFLICT (project_id,invitee_id,status) DO UPDATE SET created_at=now(), responded_at=NULL
            RETURNING id,project_id,inviter_id,invitee_id,status,created_at,responded_at
            """,
            project_id, user_id, payload.user_id,
        )
    return dict(row)

@router.get("/invitations", response_model=list[InvitationResponse])
async def list_invitations(user=Depends(current_user)):
    async with connection() as conn:
        rows = await conn.fetch(
            "SELECT id,project_id,inviter_id,invitee_id,status,created_at,responded_at FROM project_invitations WHERE invitee_id=$1 AND status='pending' ORDER BY created_at DESC",
            user[0],
        )
    return [dict(row) for row in rows]

@router.post("/invitations/{invitation_id}/accept", response_model=InvitationResponse)
async def accept_invitation(invitation_id: int, user=Depends(current_user)):
    async with connection() as conn:
        async with conn.transaction():
            row = await conn.fetchrow(
                "SELECT * FROM project_invitations WHERE id=$1 AND invitee_id=$2 AND status='pending' FOR UPDATE",
                invitation_id, user[0],
            )
            if not row:
                raise HTTPException(404, "Pending invitation not found")
            await conn.execute(
                "INSERT INTO project_members(project_id,user_id,role) VALUES($1,$2,'member') ON CONFLICT DO NOTHING",
                row["project_id"], user[0],
            )
            result = await conn.fetchrow(
                "UPDATE project_invitations SET status='accepted',responded_at=now() WHERE id=$1 RETURNING id,project_id,inviter_id,invitee_id,status,created_at,responded_at",
                invitation_id,
            )
    return dict(result)

@router.post("/invitations/{invitation_id}/reject", response_model=InvitationResponse)
async def reject_invitation(invitation_id: int, user=Depends(current_user)):
    async with connection() as conn:
        row = await conn.fetchrow(
            "UPDATE project_invitations SET status='rejected',responded_at=now() WHERE id=$1 AND invitee_id=$2 AND status='pending' RETURNING id,project_id,inviter_id,invitee_id,status,created_at,responded_at",
            invitation_id, user[0],
        )
    if not row:
        raise HTTPException(404, "Pending invitation not found")
    return dict(row)

@router.get("/{project_id}/members")
async def list_members(project_id: int, user=Depends(current_user)):
    user_id = user[0]
    async with connection() as conn:
        allowed = await conn.fetchval("SELECT 1 FROM project_members WHERE project_id=$1 AND user_id=$2", project_id, user_id)
        if not allowed:
            raise HTTPException(403, "Project membership required")
        rows = await conn.fetch("SELECT u.id,u.email,u.name,pm.role,pm.joined_at FROM project_members pm JOIN users u ON u.id=pm.user_id WHERE pm.project_id=$1 ORDER BY pm.joined_at", project_id)
        return [dict(row) for row in rows]
