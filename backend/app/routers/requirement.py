from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.store.session_store import session_store
from app.services.requirement_builder import extract_requirement

router = APIRouter(tags=["requirement"])


class UpdateFieldRequest(BaseModel):
    key: str
    value: str


class UpdateDimensionRequest(BaseModel):
    fields: list[UpdateFieldRequest]


class UpdateRequirementRequest(BaseModel):
    dimensions: Optional[dict[str, UpdateDimensionRequest]] = None


def _requirement_to_dict(session_id: str, requirement) -> dict:
    dims = {}
    for dim in requirement.dimensions:
        fields = [
            {"key": f.key, "label": f.label, "value": f.value, "editable": f.editable}
            for f in dim.fields
        ]
        dims[dim.key] = {"key": dim.key, "label": dim.label, "fields": fields}
    return {"session_id": session_id, "dimensions": dims, "version": requirement.version}


@router.get("/requirement/{session_id}")
async def get_requirement(session_id: str):
    session = session_store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session.requirement:
        # Extract requirement from dialogue
        requirement = await extract_requirement(session.messages)
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

    session.requirement.version += 1
    session_store.update(session_id, session)

    return _requirement_to_dict(session_id, session.requirement)
