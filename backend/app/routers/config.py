import json
import os

from fastapi import APIRouter
from pydantic import BaseModel

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "user_config.json")

router = APIRouter(tags=["config"])


def _load_config() -> dict:
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_config(data: dict):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_user_api_keys() -> dict:
    cfg = _load_config()
    keys = cfg.get("api_keys", {})
    return {
        "deepseek_api_key": keys.get("deepseek_api_key", ""),
        "doubao_api_key": keys.get("doubao_api_key", ""),
        "openai_api_key": keys.get("openai_api_key", ""),
    }


def _mask(key: str) -> str:
    if not key or len(key) <= 8:
        return "****" if key else ""
    return key[:4] + "****" + key[-4:]


class ApiKeysRequest(BaseModel):
    deepseek_api_key: str | None = None
    doubao_api_key: str | None = None
    openai_api_key: str | None = None


@router.get("/config/keys")
async def get_keys():
    keys = get_user_api_keys()
    return {
        "deepseek_api_key": _mask(keys["deepseek_api_key"]),
        "doubao_api_key": _mask(keys["doubao_api_key"]),
        "openai_api_key": _mask(keys["openai_api_key"]),
    }


@router.post("/config/keys")
async def save_keys(req: ApiKeysRequest):
    cfg = _load_config()
    current = cfg.get("api_keys", {})
    for field in ("deepseek_api_key", "doubao_api_key", "openai_api_key"):
        val = getattr(req, field)
        if val is not None:
            current[field] = val
    cfg["api_keys"] = current
    _save_config(cfg)
    return {
        "deepseek_api_key": _mask(current.get("deepseek_api_key", "")),
        "doubao_api_key": _mask(current.get("doubao_api_key", "")),
        "openai_api_key": _mask(current.get("openai_api_key", "")),
    }
