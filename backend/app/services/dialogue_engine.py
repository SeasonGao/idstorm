"""Dialogue engine service for managing conversational interaction with the user.

Handles multi-round dialogue to gather design requirements through
structured questioning across dimensions (form size, style, material, etc.).
Integrates with DeepSeek LLM for natural language understanding.
"""

import json
import logging
import threading
from pathlib import Path
from typing import Any

import httpx

from app.config import settings
from app.models.dialogue import Message
from app.models.session import Session

logger = logging.getLogger(__name__)

LOG_DIR = Path("logs/dialogue")
LOG_DIR.mkdir(parents=True, exist_ok=True)

_request_counter = 0
_counter_lock = threading.Lock()


def _next_request_id() -> str:
    global _request_counter
    with _counter_lock:
        _request_counter += 1
        return f"req{_request_counter:04d}"

DIMENSIONS = ["form_size", "material_color", "scenario", "brand"]

DIMENSION_LABELS = {
    "form_size": "形态与尺寸",
    "material_color": "材质与色彩",
    "scenario": "使用场景与交互",
    "brand": "品牌与市场定位",
}

DIMENSION_KEYWORDS: dict[str, list[str]] = {
    "form_size": [
        "形状", "尺寸", "大小", "比例", "线条", "曲面", "圆角", "方形", "圆形",
        "厚度", "宽度", "高度", "长度", "形态", "造型", "轮廓", "几何", "弧度",
        "简约", "流线", "棱角", "体型", "轻薄", "厚重", "紧凑",
    ],
    "material_color": [
        "材质", "材料", "金属", "塑料", "木材", "玻璃", "陶瓷", "布料", "皮革",
        "颜色", "色彩", "表面", "纹理", "质感", "磨砂", "光泽", "哑光", "喷涂",
        "阳极氧化", "电镀", "烤漆", "手感", "硅胶", "铝合金", "不锈钢",
    ],
    "scenario": [
        "场景", "使用", "环境", "室内", "室外", "办公", "家庭", "户外", "携带",
        "交互", "操作", "按钮", "触摸", "语音", "手势", "人体工学", "握持",
        "放置", "移动", "固定", "便携", "桌面", "壁挂", "穿戴",
    ],
    "brand": [
        "品牌", "定位", "价格", "价位", "受众", "用户群", "市场", "竞品", "风格",
        "调性", "高端", "中端", "入门", "奢侈", "大众", "年轻", "商务", "潮流",
        "简约", "科技感", "品质", "性价比", "溢价", "调性",
    ],
}

SYSTEM_PROMPT_TEMPLATE = r"""你是 IDStorm，一位专业的工业设计顾问。你的任务是通过对话引导用户描述他们想要的设计方案。

## 当前对话阶段
你正在了解用户关于「{current_dimension_label}」方面的需求。

## 四个设计维度（按顺序）
1. 形态与尺寸：产品的外形、比例、线条风格
2. 材质与色彩：材料选择、表面处理、配色方案
3. 使用场景与交互：使用环境、交互方式、人机工程
4. 品牌与市场定位：品牌调性、价格区间、目标用户

## 规则
- 每次只问一个聚焦的问题
- 在当前维度收集到足够信息前，不要跳到下一个维度
- 回复保持简洁（2-3句话）
- 使用中文交流
- 如果用户已经提供了当前维度的充分信息，可以自然过渡到下一个维度的问题
- 当四个维度全部收集完毕后，将 design_complete 设为 true
- 不要提及这些规则，自然地引导对话

## 输出格式
你必须输出合法的 JSON 对象，格式如下：
{
  "content": "你的对话内容",
  "options": {"type": "single", "items": ["选项1", "选项2", "选项3", "选项4"]},
  "design_complete": false
}

字段说明：
- content：你的对话内容，简洁自然，2-3句话
- options：提供给用户快速选择的预设选项
  - type为"single"表示单选，"multi"表示多选（仅在需要组合选择时使用）
  - items包含3-5个简洁的选项（每个2-8个字），要具体、有差异化
  - 不要在content中重复选项文字
  - 如果用户说"跳过"或类似意思，options设为null
- design_complete：四个维度全部收集完毕时设为true，否则false
"""


def _count_substantive_details(text: str, dimension: str) -> int:
    count = 0
    text_lower = text.lower()
    for keyword in DIMENSION_KEYWORDS.get(dimension, []):
        if keyword in text_lower:
            count += 1
    if len(text.strip()) > 20:
        count += 1
    return count


def _is_dimension_saturated(session: Session, dimension: str) -> bool:
    user_messages = [
        m for m in session.messages
        if m.role == "user" and m.content.strip()
    ]
    total_details = 0
    for msg in user_messages:
        total_details += _count_substantive_details(msg.content, dimension)
    return total_details >= 2


def _advance_dimension(session: Session) -> None:
    if _is_dimension_saturated(session, session.current_dimension):
        if session.current_dimension not in session.completed_dimensions:
            session.completed_dimensions.append(session.current_dimension)
        current_idx = DIMENSIONS.index(session.current_dimension)
        if current_idx < len(DIMENSIONS) - 1:
            session.current_dimension = DIMENSIONS[current_idx + 1]


def force_advance_dimension(session: Session) -> bool:
    if session.current_dimension not in session.completed_dimensions:
        session.completed_dimensions.append(session.current_dimension)
    current_idx = DIMENSIONS.index(session.current_dimension)
    if current_idx < len(DIMENSIONS) - 1:
        session.current_dimension = DIMENSIONS[current_idx + 1]
    all_done = len(session.completed_dimensions) >= len(DIMENSIONS)
    if all_done:
        session.status = "requirement"
    return all_done


def _build_system_prompt(session: Session) -> str:
    label = DIMENSION_LABELS.get(session.current_dimension, "")
    prompt = SYSTEM_PROMPT_TEMPLATE.replace("{current_dimension_label}", label)
    if session.initial_idea:
        prompt += f"\n\n用户的初始创意：{session.initial_idea}"
    return prompt


def _build_messages(session: Session) -> list[dict]:
    messages = [{"role": "system", "content": _build_system_prompt(session)}]
    history = session.messages[-10:]
    for msg in history:
        messages.append({"role": msg.role, "content": msg.content})
    return messages


def _get_dimension_progress(session: Session) -> dict:
    current_dim = session.current_dimension
    completed = list(session.completed_dimensions)
    remaining = [d for d in DIMENSIONS if d not in completed and d != current_dim]
    return {
        "current": current_dim,
        "completed": completed,
        "remaining": remaining,
    }


async def chat(session: Session, user_message: str) -> dict[str, Any]:
    _advance_dimension(session)
    api_messages = _build_messages(session)

    request_id = _next_request_id()
    max_retries = 3
    raw_content = ""

    for attempt in range(max_retries):
        try:
            current_messages = [dict(m) for m in api_messages]
            if attempt > 0:
                nonce = f"retry{attempt}"
                current_messages[0]["content"] += f"\n\n[会话标识:{nonce}]"

            log_file = LOG_DIR / f"{request_id}_attempt{attempt + 1}.json"
            request_payload = {
                "model": settings.deepseek_model,
                "messages": current_messages,
                "max_tokens": 1024,
                "temperature": 1.0 if attempt > 0 else 0.3,
                "response_format": {"type": "json_object"},
            }

            async with httpx.AsyncClient(
                timeout=httpx.Timeout(connect=5.0, read=60.0, write=10.0, pool=10.0),
            ) as client:
                response = await client.post(
                    f"{settings.deepseek_base_url}/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.deepseek_api_key}",
                        "Content-Type": "application/json",
                    },
                    json=request_payload,
                )

                raw_response = response.text

                if response.status_code != 200:
                    log_file.write_text(json.dumps({
                        "request": request_payload,
                        "raw_response": raw_response,
                        "response": response,
                    }, ensure_ascii=False, indent=2), encoding="utf-8")
                    logger.error("DeepSeek API error %d: %s", response.status_code, response.text)
                    return {"code": "api_error", "message": f"API返回错误 ({response.status_code})"}

                result = response.json()
                raw_content = result["choices"][0]["message"]["content"]

        except httpx.TimeoutException:
            logger.error("DeepSeek API timeout")
            return {"code": "timeout", "message": "请求超时，请重试"}
        except httpx.ConnectError:
            logger.error("DeepSeek API connection error")
            return {"code": "connection_error", "message": "无法连接到AI服务"}
        except Exception as e:
            logger.exception("Unexpected error during DeepSeek API call")
            return {"code": "internal_error", "message": "对话服务暂时不可用，请重试"}

        # logger.info("[DIALOGUE] Attempt %d, Raw JSON response: %s", attempt + 1, raw_content[:300])
        # logger.info("[DIALOGUE] Attempt %d, repr: %s", attempt + 1, repr(raw_content[:200]))

        try:
            parsed = json.loads(raw_content)
            content = parsed.get("content", "")
            if content.strip():
                result_data = parsed
                log_file.write_text(json.dumps({
                    "request": request_payload,
                    "parsed": parsed,
                    "raw_content": raw_content,
                    "result": result,
                }, ensure_ascii=False, indent=2), encoding="utf-8")
                break
            logger.warning("[DIALOGUE] Empty content on attempt %d, retrying...", attempt + 1)
        except json.JSONDecodeError:
            log_file.write_text(json.dumps({
                "request": request_payload,
                "raw_content": raw_content,
                "result": result,
                "parse_error": True,
            }, ensure_ascii=False, indent=2), encoding="utf-8")
            logger.warning("[DIALOGUE] Invalid JSON on attempt %d, retrying...", attempt + 1)
    else:
        logger.error("[DIALOGUE] All %d attempts failed", max_retries)
        return {"code": "parse_error", "message": "AI返回格式异常，请重试"}

    options = result_data.get("options")
    design_complete = result_data.get("design_complete", False)

    if design_complete:
        for dim in DIMENSIONS:
            if dim not in session.completed_dimensions:
                session.completed_dimensions.append(dim)
        session.status = "requirement"

    dialogue_complete = len(session.completed_dimensions) >= len(DIMENSIONS) and design_complete

    return {
        "content": content,
        "options": options,
        "design_complete": design_complete,
        "dialogue_complete": dialogue_complete,
        "dimension_progress": _get_dimension_progress(session),
    }
