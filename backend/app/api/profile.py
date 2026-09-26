"""Resume upload + AI Profile Understanding review (plan v5 Phase 5 / 5b), and file downloads."""
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.api.deps import get_current_user, require_role, require_tenant_scope
from app.models.tenant import Tenant
from app.models.user import User
from app.services import files, profile_ai

router = APIRouter(tags=["profile (resume)"])
candidate = require_role(["candidate"])

RESUME_KINDS = ("pdf", "docx")
RESUME_MAX_MB = 5


@router.post("/me/resume")
async def upload_resume(
    background: BackgroundTasks,
    file: UploadFile = File(...),
    user: User = Depends(candidate),
    tenant: Tenant = Depends(require_tenant_scope),
) -> dict:
    doc = await files.save(tenant.id, user.id, file, RESUME_KINDS, "resume", RESUME_MAX_MB)
    claim = await profile_ai.start(tenant.id, user.id, doc)
    background.add_task(profile_ai.run, tenant.id, claim["id"])
    return claim


@router.get("/me/resume")
async def my_resume(user: User = Depends(candidate), tenant: Tenant = Depends(require_tenant_scope)) -> dict:
    """The latest resume and what AI Profile Understanding found in it (poll while status is 'processing')."""
    return {"claim": await profile_ai.latest(tenant.id, user.id)}


@router.put("/me/resume/{claim_id}")
async def confirm_resume(
    claim_id: str, body: profile_ai.ResumeProfile, user: User = Depends(candidate), tenant: Tenant = Depends(require_tenant_scope)
) -> dict:
    """The candidate confirms — or corrects — the parsed profile. The confirmed version is what scoring uses."""
    return await profile_ai.confirm(tenant.id, user.id, claim_id, body)


@router.post("/me/resume/{claim_id}/retry")
async def retry_resume(
    claim_id: str, background: BackgroundTasks, user: User = Depends(candidate), tenant: Tenant = Depends(require_tenant_scope)
) -> dict:
    claim = await profile_ai.retry(tenant.id, user.id, claim_id)
    background.add_task(profile_ai.run, tenant.id, claim_id)
    return claim


@router.get("/files/{file_id}")
async def download(file_id: str, user: User = Depends(get_current_user), tenant: Tenant = Depends(require_tenant_scope)) -> FileResponse:
    doc = await files.get(tenant.id, file_id)
    if doc["user_id"] != user.id and user.role != "admin":
        raise HTTPException(404, "File not found")
    return FileResponse(files.path_of(doc), media_type=doc["content_type"], filename=doc["filename"])
