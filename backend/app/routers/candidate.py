import json
import logging
import os

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.config import IMAGES_DIR, settings
from app.services.image_generator import generate_candidate_images
from app.services.image_prompt_builder import build_image_prompts
from app.store.session_store import session_store

router = APIRouter(tags=["candidate"])

logger = logging.getLogger(__name__)


class GenerateRequest(BaseModel):
    session_id: str
    image_model: str | None = None  # "doubao" or "openai", defaults to config


class RegenerateImageRequest(BaseModel):
    session_id: str
    candidate_id: str
    view: str  # "orthographic" | "render"
    image_model: str | None = None


@router.post("/candidate/generate")
async def generate_candidates(req: GenerateRequest):
    session = session_store.get(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if not session.requirement:
        raise HTTPException(status_code=400, detail="Requirement not set")

    session.status = "generating"
    session_store.update(req.session_id, session)

    try:
        # Build 6 prompts (3 candidates x 2 views)
        prompts = await build_image_prompts(session.requirement)

        # Generate all images in parallel with retry
        results = await generate_candidate_images(prompts, provider=req.image_model)

        # Organize results into candidates
        candidate_map: dict[str, dict] = {}
        for r in results:
            cid = r["candidate_id"]
            if cid not in candidate_map:
                candidate_map[cid] = {"images": [], "failed_views": [], "prompts": {}}

            if r["status"] == "ok":
                candidate_map[cid]["images"].append({
                    "id": r["image_id"],
                    "image_type": r["view"],
                    "url": f"/api/candidate/image/{r['image_id']}",
                    "prompt_used": next(
                        (p["prompt"] for p in prompts if p["candidate_id"] == cid and p["view"] == r["view"]),
                        "",
                    ),
                })
            else:
                candidate_map[cid]["failed_views"].append(r["view"])

            candidate_map[cid]["prompts"][r["view"]] = next(
                (p["prompt"] for p in prompts if p["candidate_id"] == cid and p["view"] == r["view"]), ""
            )

        # Build candidate objects
        variant_labels = {"c1": "方案A", "c2": "方案B", "c3": "方案C"}
        candidates = []
        for cid in ["c1", "c2", "c3"]:
            if cid in candidate_map:
                data = candidate_map[cid]
                status = "complete" if not data["failed_views"] else "partial"

                ortho_url = ""
                render_url = ""
                for img in data["images"]:
                    if img["image_type"] == "orthographic":
                        ortho_url = img["url"]
                    elif img["image_type"] == "render":
                        render_url = img["url"]

                candidates.append({
                    "id": cid,
                    "label": variant_labels.get(cid, cid),
                    "variant_description": "",
                    "orthographic_url": ortho_url or f"/api/candidate/placeholder/{cid}/orthographic",
                    "render_url": render_url or f"/api/candidate/placeholder/{cid}/render",
                    "status": status,
                    "failed_views": data["failed_views"],
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
    """Regenerate a single failed image."""
    session = session_store.get(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if not session.requirement or not session.candidates:
        raise HTTPException(status_code=400, detail="No candidates to regenerate")

    candidate = None
    for c in session.candidates:
        if c["id"] == req.candidate_id:
            candidate = c
            break
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    prompts_data = await build_image_prompts(session.requirement)
    target_prompt = next(
        (p for p in prompts_data if p["candidate_id"] == req.candidate_id and p["view"] == req.view),
        None,
    )
    if not target_prompt:
        raise HTTPException(status_code=400, detail="View not found")

    results = await generate_candidate_images([target_prompt], provider=req.image_model)
    result = results[0]

    if result["status"] == "ok":
        new_url = f"/api/candidate/image/{result['image_id']}"
        if req.view == "orthographic":
            candidate["orthographic_url"] = new_url
        else:
            candidate["render_url"] = new_url

        if req.view in candidate.get("failed_views", []):
            candidate["failed_views"].remove(req.view)

        if not candidate["failed_views"]:
            candidate["status"] = "complete"

        session_store.update(req.session_id, session)
        return {"candidate": candidate}
    else:
        raise HTTPException(status_code=500, detail=f"Regeneration failed: {result.get('error', 'Unknown error')}")


class IterateRequest(BaseModel):
    session_id: str
    candidate_id: str
    mode: str  # "text_edit" | "image_feedback"
    updates: dict  # varies by mode
    image_model: str | None = None


@router.post("/candidate/iterate")
async def iterate_candidate(req: IterateRequest):
    session = session_store.get(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if not session.candidates or not session.requirement:
        raise HTTPException(status_code=400, detail="No candidates or requirement")

    candidate = None
    for c in session.candidates:
        if c["id"] == req.candidate_id:
            candidate = c
            break
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    if req.mode == "text_edit":
        return await _iterate_text_edit(session, candidate, req.updates, req.session_id, req.image_model)
    elif req.mode == "image_feedback":
        return await _iterate_image_feedback(session, candidate, req.updates, req.session_id, req.image_model)
    else:
        raise HTTPException(status_code=400, detail="Invalid mode. Use 'text_edit' or 'image_feedback'")


async def _iterate_text_edit(session, candidate: dict, updates: dict, session_id: str, image_model: str | None = None):
    """Regenerate candidate with updated requirement fields."""
    req = session.requirement

    # Apply updates - updates is {field_key: new_value}
    for dim in req.dimensions:
        for f in dim.fields:
            if f.key in updates:
                f.value = updates[f.key]

    req.version += 1

    # Build prompts for just this candidate
    prompts_data = await build_image_prompts(req)
    target_prompts = [p for p in prompts_data if p["candidate_id"] == candidate["id"]]

    if not target_prompts:
        raise HTTPException(status_code=500, detail="Could not build prompts for candidate")

    # Regenerate both images for this candidate
    results = await generate_candidate_images(target_prompts, provider=image_model)

    for r in results:
        if r["status"] == "ok":
            new_url = f"/api/candidate/image/{r['image_id']}"
            if r["view"] == "orthographic":
                candidate["orthographic_url"] = new_url
            else:
                candidate["render_url"] = new_url
            if r["view"] in candidate.get("failed_views", []):
                candidate["failed_views"].remove(r["view"])
        else:
            if r["view"] not in candidate.get("failed_views", []):
                candidate.setdefault("failed_views", []).append(r["view"])

    candidate["status"] = "complete" if not candidate.get("failed_views") else "partial"

    session_store.update(session_id, session)
    return {"candidate": candidate}


async def _iterate_image_feedback(session, candidate: dict, updates: dict, session_id: str, image_model: str | None = None):
    """Interpret image feedback via DeepSeek and regenerate."""
    annotation_text = updates.get("annotation_text", "")
    if not annotation_text:
        raise HTTPException(status_code=400, detail="annotation_text is required for image_feedback mode")

    # Build current requirement summary
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
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{settings.deepseek_base_url}/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.deepseek_api_key}"},
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

            # Only keep modifications with valid field keys
            valid_keys = {f.key for dim in session.requirement.dimensions for f in dim.fields}
            modifications = {k: str(v) for k, v in modifications.items() if k in valid_keys}
    except Exception as e:
        logger.exception("Failed to interpret image feedback for session %s", session_id)
        raise HTTPException(status_code=500, detail="反馈处理失败，请重试")

    if not modifications:
        return {"candidate": candidate, "message": "未识别到需要修改的内容"}

    return await _iterate_text_edit(session, candidate, modifications, session_id, image_model)
