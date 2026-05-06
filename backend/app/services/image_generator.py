"""Image generator service for producing candidate design images.

Supports two image generation providers:
- Doubao Seedream (default): Volcengine/ByteDance API
- OpenAI GPT-Image-2: OpenAI Images API

Dispatches to the correct provider based on the `image_model` parameter.
"""

import asyncio
import base64
import logging
import os
import uuid

import httpx

from app.config import IMAGES_DIR, settings

logger = logging.getLogger(__name__)

VALID_PROVIDERS = ("doubao", "openai")


def _get_default_provider() -> str:
    provider = settings.default_image_provider
    return provider if provider in VALID_PROVIDERS else "doubao"


# ---------------------------------------------------------------------------
# Doubao Seedream
# ---------------------------------------------------------------------------

async def _generate_doubao(prompt: str, api_key: str | None = None) -> tuple[str, str]:
    """Generate a single image using Doubao Seedream API.

    Returns (image_id, file_path).
    """
    os.makedirs(IMAGES_DIR, exist_ok=True)

    key = api_key or settings.doubao_api_key

    payload = {
        "model": settings.doubao_model,
        "prompt": prompt,
        "sequential_image_generation": "disabled",
        "response_format": "url",
        "size": settings.doubao_image_size,
        "stream": False,
        "watermark": True,
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{settings.doubao_base_url}/images/generations",
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        if response.status_code != 200:
            logger.error("[DOUBAO] status=%s body=%s", response.status_code, response.text[:500])
        response.raise_for_status()
        result = response.json()

    image_data = result["data"][0]
    image_id = str(uuid.uuid4())

    if "url" in image_data:
        async with httpx.AsyncClient(timeout=60.0) as dl_client:
            img_response = await dl_client.get(image_data["url"])
            img_response.raise_for_status()
            file_path = os.path.join(IMAGES_DIR, f"{image_id}.jpg")
            with open(file_path, "wb") as f:
                f.write(img_response.content)
    elif "b64_json" in image_data:
        file_path = os.path.join(IMAGES_DIR, f"{image_id}.jpg")
        with open(file_path, "wb") as f:
            f.write(base64.b64decode(image_data["b64_json"]))
    else:
        raise ValueError("Unexpected Doubao response format")

    return image_id, file_path


# ---------------------------------------------------------------------------
# OpenAI GPT-Image-2
# ---------------------------------------------------------------------------

async def _generate_openai(prompt: str, size: str = "1024x1024", api_key: str | None = None) -> tuple[str, str]:
    """Generate a single image using OpenAI Images API.

    Returns (image_id, file_path).
    """
    os.makedirs(IMAGES_DIR, exist_ok=True)

    key = api_key or settings.openai_api_key

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            "https://api.openai.com/v1/images/generations",
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "gpt-image-2",
                "prompt": prompt,
                "n": 1,
                "size": size,
            },
        )
        response.raise_for_status()
        result = response.json()

    image_data = result["data"][0]
    image_id = str(uuid.uuid4())

    if "b64_json" in image_data:
        file_path = os.path.join(IMAGES_DIR, f"{image_id}.png")
        with open(file_path, "wb") as f:
            f.write(base64.b64decode(image_data["b64_json"]))
    elif "url" in image_data:
        async with httpx.AsyncClient(timeout=60.0) as dl_client:
            img_response = await dl_client.get(image_data["url"])
            img_response.raise_for_status()
            file_path = os.path.join(IMAGES_DIR, f"{image_id}.png")
            with open(file_path, "wb") as f:
                f.write(img_response.content)
    else:
        raise ValueError("Unexpected OpenAI response format")

    return image_id, file_path


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

async def generate_image(prompt: str, provider: str | None = None, api_keys: dict | None = None) -> tuple[str, str]:
    """Generate a single image using the specified provider.

    Args:
        prompt: Image generation prompt.
        provider: "doubao" or "openai". Defaults to settings.default_image_provider.
        api_keys: Optional dict with user-provided API keys.

    Returns (image_id, file_path).
    """
    provider = provider or _get_default_provider()
    keys = api_keys or {}

    if provider == "doubao":
        return await _generate_doubao(prompt, api_key=keys.get("doubao_api_key"))
    elif provider == "openai":
        return await _generate_openai(prompt, settings.image_size, api_key=keys.get("openai_api_key"))
    else:
        raise ValueError(f"Unknown image provider: {provider}")


async def generate_candidate_images(
    prompts: list[dict],
    provider: str | None = None,
    api_keys: dict | None = None,
) -> list[dict]:
    """Generate all images for candidates with retry and partial failure handling.

    prompts: list of {"candidate_id": "c1", "view": "orthographic", "prompt": "..."}
    provider: "doubao" or "openai". Defaults to settings.default_image_provider.
    api_keys: Optional dict with user-provided API keys.

    Returns list of results:
    - On success: {"candidate_id": ..., "view": ..., "image_id": ..., "file_path": ..., "status": "ok"}
    - On failure after retries: {"candidate_id": ..., "view": ..., "status": "failed", "error": ...}
    """
    resolved_provider = provider or _get_default_provider()

    async def generate_with_retry(prompt_text: str, candidate_id: str, view: str, retries: int = 2) -> dict:
        last_error = None
        for attempt in range(retries + 1):
            try:
                image_id, file_path = await generate_image(prompt_text, resolved_provider, api_keys=api_keys)
                return {
                    "candidate_id": candidate_id,
                    "view": view,
                    "image_id": image_id,
                    "file_path": file_path,
                    "status": "ok",
                }
            except Exception as e:
                last_error = str(e)
                logger.warning(
                    "Image generation failed (attempt %d/%d) for %s/%s [%s]: %s",
                    attempt + 1, retries + 1, candidate_id, view, resolved_provider, e,
                )
                if attempt < retries:
                    await asyncio.sleep(3 * (attempt + 1))

        return {
            "candidate_id": candidate_id,
            "view": view,
            "status": "failed",
            "error": last_error,
        }

    tasks = [generate_with_retry(p["prompt"], p["candidate_id"], p["view"]) for p in prompts]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    processed = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            processed.append({
                "candidate_id": prompts[i]["candidate_id"],
                "view": prompts[i]["view"],
                "status": "failed",
                "error": str(result),
            })
        else:
            processed.append(result)

    return processed
