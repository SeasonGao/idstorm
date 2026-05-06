from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.store.session_store import session_store
from app.services.requirement_builder import extract_requirement
from app.routers.config import get_user_api_keys

router = APIRouter(tags=["requirement"])


class UpdateFieldRequest(BaseModel):
    key: str
    value: str


class UpdateDimensionRequest(BaseModel):
    fields: list[UpdateFieldRequest]


class UpdateRequirementRequest(BaseModel):
    dimensions: Optional[dict[str, UpdateDimensionRequest]] = None
    product_name: Optional[str] = None
    three_view_desc: Optional[str] = None
    scene_desc: Optional[str] = None


def _requirement_to_dict(session_id: str, requirement) -> dict:
    dims = {}
    for dim in requirement.dimensions:
        fields = [
            {"key": f.key, "label": f.label, "value": f.value, "editable": f.editable}
            for f in dim.fields
        ]
        dims[dim.key] = {"key": dim.key, "label": dim.label, "fields": fields}
    return {
        "session_id": session_id,
        "dimensions": dims,
        "version": requirement.version,
        "product_name": requirement.product_name,
        "three_view_desc": requirement.three_view_desc,
        "scene_desc": requirement.scene_desc,
    }


@router.get("/requirement/{session_id}")
async def get_requirement(session_id: str):
    session = session_store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session.requirement:
        # Extract requirement from dialogue
        requirement = await extract_requirement(session.messages, api_keys=get_user_api_keys())
        session.requirement = requirement
        session.status = "requirement"
        session_store.update(session_id, session)

    return _requirement_to_dict(session_id, session.requirement)


@router.post("/requirement/{session_id}/regenerate")
async def regenerate_requirement(session_id: str):
    """Re-extract requirement from dialogue messages."""
    session = session_store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    requirement = await extract_requirement(session.messages, api_keys=get_user_api_keys())
    session.requirement = requirement
    session.status = "requirement"
    session_store.update(session_id, session)

    return _requirement_to_dict(session_id, session.requirement)


@router.put("/requirement/{session_id}")
async def update_requirement(session_id: str, req: UpdateRequirementRequest):
    session = session_store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session.requirement:
        raise HTTPException(status_code=400, detail="Requirement not yet extracted")

    if req.dimensions:
        for dim_key, dim_update in req.dimensions.items():
            for dim in session.requirement.dimensions:
                if dim.key == dim_key:
                    for field_update in dim_update.fields:
                        for f in dim.fields:
                            if f.key == field_update.key:
                                f.value = field_update.value

    if req.product_name is not None:
        session.requirement.product_name = req.product_name
    if req.three_view_desc is not None:
        session.requirement.three_view_desc = req.three_view_desc
    if req.scene_desc is not None:
        session.requirement.scene_desc = req.scene_desc

    session.requirement.version += 1
    session_store.update(session_id, session)

    return _requirement_to_dict(session_id, session.requirement)
