import json
import logging
import os

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.config import IMAGES_DIR, settings
from app.routers.config import get_user_api_keys
from app.services.image_generator import generate_candidate_images, generate_image_to_image
from app.services.image_prompt_builder import build_image_prompts
from app.store.session_store import session_store
from datetime import datetime

router = APIRouter(tags=["candidate"])

logger = logging.getLogger(__name__)

LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


class GenerateRequest(BaseModel):
    session_id: str
    image_model: str | None = None
    candidate_count: int = 3


class RegenerateImageRequest(BaseModel):
    session_id: str
    candidate_id: str
    image_model: str | None = None


@router.get("/candidate/{session_id}")
async def get_candidates(session_id: str):
    session = session_store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"candidates": session.candidates or []}


@router.post("/candidate/generate")
async def generate_candidates(req: GenerateRequest):
    session = session_store.get(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if not session.requirement:
        raise HTTPException(status_code=400, detail="Requirement not set")

    count = max(1, min(5, req.candidate_count))
    api_keys = get_user_api_keys()

    session.status = "generating"
    session_store.update(req.session_id, session)

    try:
        prompts = await build_image_prompts(session.requirement, count=count, api_keys=api_keys)
        results = await generate_candidate_images(prompts, provider=req.image_model, api_keys=api_keys)

        # Build candidate objects from results
        candidate_ids = [f"c{i+1}" for i in range(count)]
        prompt_map = {p["candidate_id"]: p["prompt"] for p in prompts}
        result_map = {r["candidate_id"]: r for r in results}

        candidates = []
        for idx, cid in enumerate(candidate_ids):
            r = result_map.get(cid)
            if r and r["status"] == "ok":
                image_url = f"/api/candidate/image/{r['image_id']}"
                status = "complete"
            else:
                image_url = ""
                status = "failed"

            candidates.append({
                "id": cid,
                "label": f"方案{LETTERS[idx]}",
                "variant_description": "",
                "image_url": image_url,
                "prompt": prompt_map.get(cid, ""),
                "status": status,
                "images": [{
                    "id": r["image_id"] if r and r["status"] == "ok" else "",
                    "url": image_url,
                    "feedback": None,
                    "parent_image_id": None,
                    "created_at": datetime.now().isoformat(),
                }] if status == "complete" else [],
            })

        session.candidates = candidates
        session.status = "review"
        session_store.update(req.session_id, session)

        return {"candidates": candidates}

    except Exception as e:
        logger.exception("Candidate generation failed for session %s", req.session_id)
        session.status = "requirement"
        session_store.update(req.session_id, session)
        raise HTTPException(status_code=500, detail="图像生成失败，请重试")


@router.get("/candidate/image/{image_id}")
async def get_image(image_id: str):
    """Serve a generated image file."""
    if "/" in image_id or "\\" in image_id or ".." in image_id:
        raise HTTPException(status_code=400, detail="Invalid image ID")

    for ext, media in [(".png", "image/png"), (".jpg", "image/jpeg")]:
        file_path = os.path.join(IMAGES_DIR, f"{image_id}{ext}")
        if os.path.exists(file_path):
            return FileResponse(file_path, media_type=media)

    raise HTTPException(status_code=404, detail="Image not found")


@router.post("/candidate/image/regenerate")
async def regenerate_image(req: RegenerateImageRequest):
    """Regenerate a single candidate image."""
    session = session_store.get(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if not session.requirement or not session.candidates:
        raise HTTPException(status_code=400, detail="No candidates to regenerate")

    candidate = _find_candidate(session, req.candidate_id)
    api_keys = get_user_api_keys()

    # Rebuild the prompt for this candidate
    prompts_data = await build_image_prompts(session.requirement, api_keys=api_keys)
    target_prompt = next((p for p in prompts_data if p["candidate_id"] == req.candidate_id), None)
    if not target_prompt:
        raise HTTPException(status_code=400, detail="Candidate prompt not found")

    results = await generate_candidate_images([target_prompt], provider=req.image_model, api_keys=api_keys)
    result = results[0]

    if result["status"] == "ok":
        new_url = f"/api/candidate/image/{result['image_id']}"
        candidate["image_url"] = new_url
        candidate["status"] = "complete"
        # Append to image history
        images = candidate.get("images", [])
        images.append({
            "id": result["image_id"],
            "url": new_url,
            "feedback": None,
            "parent_image_id": images[-1]["id"] if images else None,
            "created_at": datetime.now().isoformat(),
        })
        candidate["images"] = images
        session_store.update(req.session_id, session)
        return {"candidate": candidate}
    else:
        raise HTTPException(status_code=500, detail=f"Regeneration failed: {result.get('error', 'Unknown error')}")


class IterateRequest(BaseModel):
    session_id: str
    candidate_id: str
    mode: str  # "text_edit" | "image_feedback"
    updates: dict
    image_model: str | None = None


class ImageIterateRequest(BaseModel):
    session_id: str
    candidate_id: str
    base_image_id: str | None = None  # Which image to use as base; defaults to latest
    feedback_text: str
    image_model: str | None = None


@router.post("/candidate/image-iterate")
async def image_iterate(req: ImageIterateRequest):
    """Iterate on a candidate using image-to-image: base image + feedback text."""
    session = session_store.get(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if not session.candidates:
        raise HTTPException(status_code=400, detail="No candidates")

    candidate = _find_candidate(session, req.candidate_id)
    images = candidate.get("images", [])

    # Find the base image
    base_entry = None
    if req.base_image_id and images:
        base_entry = next((img for img in images if img["id"] == req.base_image_id), None)
        if not base_entry:
            raise HTTPException(status_code=400, detail="Base image not found")
    elif images:
        base_entry = images[-1]  # Default to latest image
    elif candidate.get("image_url"):
        # Backward compat: old sessions have no images array but do have image_url
        image_id = candidate["image_url"].rsplit("/", 1)[-1]
        base_entry = {"id": image_id, "url": candidate["image_url"]}
    else:
        raise HTTPException(status_code=400, detail="No image to iterate from")

    # Resolve the base image file path on disk
    base_image_id = base_entry["id"]
    base_image_path = _resolve_image_path(base_image_id)
    if not base_image_path:
        raise HTTPException(status_code=400, detail="Base image file not found on disk")

    api_keys = get_user_api_keys()

    try:
        new_image_id, _ = await generate_image_to_image(
            base_image_path, req.feedback_text,
            provider=req.image_model, api_keys=api_keys,
        )
    except Exception as e:
        logger.exception("Image-to-image iteration failed for session %s", req.session_id)
        raise HTTPException(status_code=500, detail=f"图像迭代失败: {e}")

    new_entry = {
        "id": new_image_id,
        "url": f"/api/candidate/image/{new_image_id}",
        "feedback": req.feedback_text,
        "parent_image_id": base_entry["id"],
        "created_at": datetime.now().isoformat(),
    }
    images.append(new_entry)

    candidate["images"] = images
    candidate["image_url"] = new_entry["url"]
    candidate["status"] = "complete"
    session_store.update(req.session_id, session)

    return {"candidate": candidate}


def _resolve_image_path(image_id: str) -> str | None:
    """Find the actual file path for an image_id on disk."""
    for ext in (".png", ".jpg", ".jpeg"):
        path = os.path.join(IMAGES_DIR, f"{image_id}{ext}")
        if os.path.exists(path):
            return path
    return None


@router.post("/candidate/iterate")
async def iterate_candidate(req: IterateRequest):
    session = session_store.get(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if not session.candidates or not session.requirement:
        raise HTTPException(status_code=400, detail="No candidates or requirement")

    candidate = _find_candidate(session, req.candidate_id)

    if req.mode == "text_edit":
        return await _iterate_text_edit(session, candidate, req.updates, req.session_id, req.image_model)
    elif req.mode == "image_feedback":
        return await _iterate_image_feedback(session, candidate, req.updates, req.session_id, req.image_model)
    else:
        raise HTTPException(status_code=400, detail="Invalid mode. Use 'text_edit' or 'image_feedback'")


async def _iterate_text_edit(session, candidate: dict, updates: dict, session_id: str, image_model: str | None = None):
    """Regenerate candidate with updated requirement fields."""
    api_keys = get_user_api_keys()
    req = session.requirement

    for dim in req.dimensions:
        for f in dim.fields:
            if f.key in updates:
                f.value = updates[f.key]

    req.version += 1

    prompts_data = await build_image_prompts(req, api_keys=api_keys)
    target_prompt = next((p for p in prompts_data if p["candidate_id"] == candidate["id"]), None)

    if not target_prompt:
        raise HTTPException(status_code=500, detail="Could not build prompt for candidate")

    results = await generate_candidate_images([target_prompt], provider=image_model, api_keys=api_keys)
    result = results[0]

    if result["status"] == "ok":
        new_url = f"/api/candidate/image/{result['image_id']}"
        candidate["image_url"] = new_url
        candidate["status"] = "complete"
        # Append to image history
        images = candidate.get("images", [])
        images.append({
            "id": result["image_id"],
            "url": new_url,
            "feedback": str(updates),
            "parent_image_id": images[-1]["id"] if images else None,
            "created_at": datetime.now().isoformat(),
        })
        candidate["images"] = images
    else:
        candidate["status"] = "failed"

    session_store.update(session_id, session)
    return {"candidate": candidate}


async def _iterate_image_feedback(session, candidate: dict, updates: dict, session_id: str, image_model: str | None = None):
    """Interpret image feedback via DeepSeek and regenerate."""
    api_keys = get_user_api_keys()
    annotation_text = updates.get("annotation_text", "")
    if not annotation_text:
        raise HTTPException(status_code=400, detail="annotation_text is required for image_feedback mode")

    fields_summary = ""
    for dim in session.requirement.dimensions:
        fields_summary += f"\n{dim.label}:\n"
        for f in dim.fields:
            fields_summary += f"  {f.label}: {f.value}\n"

    interpret_prompt = f"""你是一个设计需求修改顾问。用户对当前的设计方案给出了反馈。

当前设计需求：
{fields_summary}

用户反馈："{annotation_text}"

请根据用户反馈，输出需要修改的字段。只输出需要修改的字段，不需要修改的字段不要包含。

输出JSON格式：
{{"field_key": "新值", ...}}

只输出JSON，不要其他文字。如果没有需要修改的字段，输出空JSON：{{}}"""

    try:
        deepseek_key = api_keys.get("deepseek_api_key") or settings.deepseek_api_key
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{settings.deepseek_base_url}/v1/chat/completions",
                headers={"Authorization": f"Bearer {deepseek_key}"},
                json={
                    "model": settings.deepseek_model,
                    "messages": [{"role": "user", "content": interpret_prompt}],
                    "temperature": 0.3,
                },
            )
            response.raise_for_status()
            result = response.json()
            content = result["choices"][0]["message"]["content"].strip()

            if content.startswith("```"):
                content = content.split("\n", 1)[1] if "\n" in content else content[3:]
                if content.endswith("```"):
                    content = content[:-3]
                content = content.strip()

            modifications = json.loads(content)

            valid_keys = {f.key for dim in session.requirement.dimensions for f in dim.fields}
            modifications = {k: str(v) for k, v in modifications.items() if k in valid_keys}
    except Exception:
        logger.exception("Failed to interpret image feedback for session %s", session_id)
        raise HTTPException(status_code=500, detail="反馈处理失败，请重试")

    if not modifications:
        return {"candidate": candidate, "message": "未识别到需要修改的内容"}

    return await _iterate_text_edit(session, candidate, modifications, session_id, image_model)


def _find_candidate(session, candidate_id: str) -> dict:
    for c in session.candidates:
        if c["id"] == candidate_id:
            return c
    raise HTTPException(status_code=404, detail="Candidate not found")
