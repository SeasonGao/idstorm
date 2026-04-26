"""Dialogue engine service for managing conversational interaction with the user.

Handles multi-round dialogue to gather design requirements through
structured questioning across dimensions (form size, style, material, etc.).

4-node pipeline:
  Node 1 (Decision):    Judge if current dimension is saturated
  Node 2 (Summary):     Summarize completed dimension & transition
  Node 3 (Dialogue):    Generate open-ended question for current dimension
  Node 4 (Option Gen):  Generate suggestion options for the question
"""

import asyncio
import json
import logging
import threading
from pathlib import Path
from typing import Any

from openai import OpenAI

from app.config import settings
from app.models.dialogue import Message
from app.models.session import Session

logger = logging.getLogger(__name__)

LOG_DIR = Path(__file__).parent.parent.parent / "logs" / "dialogue"
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

# ---------------------------------------------------------------------------
# Node 1: Decision Node - judge if current dimension is saturated
# ---------------------------------------------------------------------------
SYSTEM_PROMPT_DECISION = r"""你是一个信息饱和度判断器。你的任务是分析对话历史，判断当前设计维度的信息收集是否已经充分。

## 四个设计维度（按顺序）
1. 形态与尺寸（form_size）：产品的外形、比例、线条风格
2. 材质与色彩（material_color）：材料选择、表面处理、配色方案
3. 使用场景与交互（scenario）：使用环境、交互方式、人机工程
4. 品牌与市场定位（brand）：品牌调性、价格区间、目标用户

## 当前维度
{current_dimension_label}

## 判断标准
信息收集充分 = 满足以下至少2个条件：
- 用户给出了具体的风格/形态/材质/场景描述
- 用户提到了明确的关键词（非泛泛而谈）
- 用户提供了多轮有价值的细节补充
- 用户的描述足够具体，可以直接指导设计

信息不充分 = 满足以下任一条件：
- 用户只回复了"嗯"、"好"等无实质内容
- 用户只给了一个非常模糊的描述
- 对话刚进入当前维度，用户还没来得及表达

## 输出格式（严格JSON）
{
  "decision": "continue" 或 "complete",
  "reason": "简要说明判断理由"
}

## 重要
- 必须输出合法JSON
- 只有在用户确实提供了充分信息时才设为 complete
- 宁可多问一轮，也不要过早判定完成
"""

# ---------------------------------------------------------------------------
# Node 2: Summary Node - summarize completed dimension
# ---------------------------------------------------------------------------
SYSTEM_PROMPT_SUMMARY = r"""你是一个工业设计需求总结器。你的任务是将用户在某个设计维度下的对话历史，总结为一段简洁但完整的设计需求描述。

## 当前总结的维度
{current_dimension_label}

## 总结要求
1. 提取用户明确表达的所有偏好和需求
2. 保留具体的关键词和描述（如"流线型"、"磨砂质感"等）
3. 去除对话中的寒暄、重复和无效信息
4. 用第三人称客观描述，例如"用户偏好..."
5. 控制在100字以内

## 输出格式（严格JSON）
{
  "summary": "总结文本"
}

## 重要
- 必须输出合法JSON
- summary必须是字符串
- 总结要精炼，只保留对设计有指导意义的信息
"""

# ---------------------------------------------------------------------------
# Node 3: Dialogue Node - generate open-ended question
# ---------------------------------------------------------------------------
SYSTEM_PROMPT_DIALOGUE = r"""你是 IDStorm，一位专业的工业设计顾问。你的任务是通过对话引导用户描述他们想要的设计方案。

## 当前对话阶段
你正在了解用户关于「{current_dimension_label}」方面的需求。

## 已完成的维度总结
{previous_summaries}

## 核心原则
- **只做开放式提问**：问题不能包含任何选项、示例或对比
- **每次只问一个问题**，保持简洁
- 使用中文交流
- 结合已完成的维度总结，让提问更有针对性
- 在当前维度收集到足够信息前，不要跳到下一个维度

## 允许的提问方式
✅ "请描述您心目中这个产品的外观轮廓。"
✅ "您希望产品表面呈现怎样的质感？"
✅ "用户在什么场景下会使用这个产品？"

## 禁止的提问方式
❌ "您希望产品是圆的还是方的？"
❌ "您更喜欢金属、木材还是塑料？"
❌ "产品应该偏向高端还是亲民？"

## 输出要求
只输出纯问题文本，不要输出任何其他内容。
"""

# ---------------------------------------------------------------------------
# Node 4: Option Generation Node - generate options for the question
# ---------------------------------------------------------------------------
SYSTEM_PROMPT_OPTIONS = r"""你是一个智能选项生成器。根据对话节点提出的开放式问题，生成合理的建议选项供用户选择。

## 输入
对话节点的最新一次提问（开放式问题）

## 任务
1. 分析这个开放式问题的意图，判断它在收集哪个维度的信息
2. 生成3-5个该问题下最常见的、合理的建议选项

## 输出格式（严格JSON）
{
  "options": ["选项1", "选项2", "选项3", "选项4"]
}

## 选项生成规则
- 每个选项用简洁的词语或短句表达，不超过8个字
- 选项之间要有明显的区分度
- 覆盖常见的设计可能性
- 例如：
  - 问题"请描述您心目中这个产品的外观轮廓" → {"options": ["方正硬朗", "圆润柔和", "流线动感", "几何拼接", "有机自然"]}
  - 问题"您希望产品表面呈现怎样的质感" → {"options": ["高光镜面", "哑光磨砂", "粗糙肌理", "细腻亲肤", "金属拉丝"]}
  - 问题"用户主要在什么场景下使用" → {"options": ["居家客厅", "办公桌面", "户外携带", "商业空间", "车载环境"]}

## 重要
- 必须输出合法JSON，不要有任何额外文字
- options必须是数组格式，不能是对象或字符串
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


def force_advance_dimension(session: Session) -> bool:
    if session.current_dimension not in session.completed_dimensions:
        session.completed_dimensions.append(session.current_dimension)
    current_idx = DIMENSIONS.index(session.current_dimension)
    if current_idx < len(DIMENSIONS) - 1:
        session.current_dimension = DIMENSIONS[current_idx + 1]
    all_done = len(session.completed_dimensions) >= len(DIMENSIONS)
    if all_done:
        session.status = "requirement"
        session.current_dimension = ""
    return all_done


def _get_dimension_progress(session: Session) -> dict:
    current_dim = session.current_dimension
    completed = list(session.completed_dimensions)
    remaining = [d for d in DIMENSIONS if d not in completed and d != current_dim]
    return {
        "current": current_dim,
        "completed": completed,
        "remaining": remaining,
    }


def _format_previous_summaries(session: Session) -> str:
    if not session.dimension_summaries:
        return "暂无"
    parts = []
    for dim_key in DIMENSIONS:
        if dim_key in session.dimension_summaries:
            label = DIMENSION_LABELS.get(dim_key, dim_key)
            parts.append(f"- {label}：{session.dimension_summaries[dim_key]}")
    return "\n".join(parts) if parts else "暂无"


def _build_dialogue_messages(session: Session) -> list[dict]:
    label = DIMENSION_LABELS.get(session.current_dimension, "")
    summaries = _format_previous_summaries(session)
    system_content = SYSTEM_PROMPT_DIALOGUE.replace(
        "{current_dimension_label}", label
    ).replace(
        "{previous_summaries}", summaries
    )
    if session.initial_idea:
        system_content += f"\n\n用户的初始创意：{session.initial_idea}"

    messages = [{"role": "system", "content": system_content}]
    for msg in session.messages:
        messages.append({"role": msg.role, "content": msg.content})
    return messages


async def _call_model(
    messages: list[dict],
    model: str,
    temperature: float,
    response_format: dict | None = None,
) -> str:
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "max_tokens": 4096,
        "temperature": temperature,
        "extra_body": {"thinking": {"type": "disabled"}},
    }
    if response_format:
        payload["response_format"] = response_format

    def _call():
        client = OpenAI(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
        )
        return client.chat.completions.create(**payload)

    response = await asyncio.to_thread(_call)
    return response.choices[0].message.content or ""


class _RequestLogger:
    def __init__(self, request_id: str, session_id: str, user_message: str, session_snapshot: dict):
        self.request_id = request_id
        self.session_id = session_id
        self.entries: list[dict] = []
        self.meta = {
            "request_id": request_id,
            "user_message": user_message,
            "session_snapshot": session_snapshot,
        }

    def append(
        self,
        node: str,
        request_messages: list[dict],
        raw_response: str,
        parsed_result: dict | None = None,
    ) -> None:
        self.entries.append({
            "node": node,
            "request": request_messages,
            "response": raw_response,
            "parsed": parsed_result,
        })

    def flush(self, final_result: dict | None = None) -> None:
        session_log_dir = LOG_DIR / self.session_id
        session_log_dir.mkdir(parents=True, exist_ok=True)
        log_file = session_log_dir / f"{self.request_id}.json"
        log_file.write_text(
            json.dumps(
                {
                    **self.meta,
                    "nodes": self.entries,
                    "final_result": final_result,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )


async def _run_decision_node(
    session: Session, request_id: str, req_log: _RequestLogger
) -> tuple[str, str]:
    label = DIMENSION_LABELS.get(session.current_dimension, "")
    system_content = SYSTEM_PROMPT_DECISION.replace(
        "{current_dimension_label}", label
    )

    history_lines = []
    for msg in session.messages:
        role_label = "用户" if msg.role == "user" else "助手"
        history_lines.append(f"{role_label}：{msg.content}")
    history_text = "\n".join(history_lines) if history_lines else "（暂无对话历史）"

    messages = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": f"以下是对话历史：\n{history_text}"},
    ]

    raw = await _call_model(
        messages, "deepseek-v4-flash", 0.1, response_format={"type": "json_object"}
    )

    try:
        parsed = json.loads(raw)
        decision = parsed.get("decision", "continue")
        reason = parsed.get("reason", "")
        req_log.append("decision", messages, raw, parsed)
        return decision, reason
    except json.JSONDecodeError:
        logger.warning("[DECISION] Invalid JSON: %s", raw[:200])
        req_log.append("decision", messages, raw, None)
        return "continue", "JSON解析失败，默认继续"


async def _run_summary_node(
    session: Session, request_id: str, req_log: _RequestLogger
) -> str | None:
    label = DIMENSION_LABELS.get(session.current_dimension, "")
    system_content = SYSTEM_PROMPT_SUMMARY.replace(
        "{current_dimension_label}", label
    )

    history_lines = []
    for msg in session.messages[session.dimension_message_start:]:
        role_label = "用户" if msg.role == "user" else "助手"
        history_lines.append(f"{role_label}：{msg.content}")
    history_text = "\n".join(history_lines)

    messages = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": f"请总结以下对话：\n{history_text}"},
    ]

    raw = await _call_model(
        messages, "deepseek-v4-flash", 0.1, response_format={"type": "json_object"}
    )

    try:
        parsed = json.loads(raw)
        summary = parsed.get("summary", "")
        req_log.append("summary", messages, raw, parsed)
        return summary if summary else None
    except json.JSONDecodeError:
        logger.warning("[SUMMARY] Invalid JSON: %s", raw[:200])
        req_log.append("summary", messages, raw, None)
        return None


async def _run_dialogue_node(
    session: Session, request_id: str, req_log: _RequestLogger
) -> str | None:
    api_messages = _build_dialogue_messages(session)

    for attempt in range(3):
        try:
            raw = await _call_model(
                [dict(m) for m in api_messages],
                "deepseek-v4-flash",
                0.3,
            )
            if raw.strip():
                req_log.append("dialogue", api_messages, raw)
                return raw.strip()
            logger.warning("[DIALOGUE] Empty response on attempt %d", attempt + 1)
        except Exception:
            logger.exception("[DIALOGUE] Error on attempt %d", attempt + 1)

    req_log.append("dialogue", api_messages, "")
    return None


async def _run_option_node(
    question: str, request_id: str, req_log: _RequestLogger
) -> list[str] | None:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT_OPTIONS},
        {"role": "user", "content": question},
    ]

    for attempt in range(3):
        try:
            raw = await _call_model(
                messages,
                "deepseek-v4-flash",
                0.1,
                response_format={"type": "json_object"},
            )
            parsed = json.loads(raw)
            options = parsed.get("options")
            if isinstance(options, list) and options:
                req_log.append("options", messages, raw, parsed)
                return options
            logger.warning("[OPTIONS] Empty or invalid options on attempt %d", attempt + 1)
        except json.JSONDecodeError:
            logger.warning("[OPTIONS] Invalid JSON on attempt %d: %s", attempt + 1, raw[:200])
        except Exception:
            logger.exception("[OPTIONS] Error on attempt %d", attempt + 1)

    req_log.append("options", messages, "")
    return None


async def chat(session: Session, user_message: str) -> dict[str, Any]:
    request_id = _next_request_id()
    req_log = _RequestLogger(
        request_id,
        session.id,
        user_message,
        {
            "current_dimension": session.current_dimension,
            "completed_dimensions": list(session.completed_dimensions),
            "dimension_summaries": dict(session.dimension_summaries),
            "message_count": len(session.messages),
        },
    )

    # ── Node 1: Decision ──
    user_messages = [m for m in session.messages if m.role == "user" and m.content.strip()]
    needs_decision = len(user_messages) > 0
    decision = "continue"

    if needs_decision:
        try:
            decision, reason = await _run_decision_node(session, request_id, req_log)
            logger.info(
                "[DECISION] dimension=%s decision=%s reason=%s",
                session.current_dimension, decision, reason,
            )
        except Exception:
            logger.exception("[DECISION] Error, defaulting to continue")
            decision = "continue"

    # ── Node 2: Summary (if decision == "complete") ──
    if decision == "complete":
        completed_dim = session.current_dimension

        try:
            summary = await _run_summary_node(session, request_id, req_log)
        except Exception:
            logger.exception("[SUMMARY] Error, using fallback")
            summary = None

        if not summary:
            user_texts = [m.content for m in session.messages if m.role == "user"]
            summary = "；".join(user_texts[-3:])

        session.dimension_summaries[completed_dim] = summary
        if completed_dim not in session.completed_dimensions:
            session.completed_dimensions.append(completed_dim)

        current_idx = DIMENSIONS.index(completed_dim)
        is_last_dimension = current_idx >= len(DIMENSIONS) - 1

        if is_last_dimension:
            session.status = "requirement"
            session.current_dimension = ""
            result = {
                "content": "好的，我们已经完成了所有维度的信息收集，接下来将为您生成设计方案。",
                "options": None,
                "design_complete": True,
                "dialogue_complete": True,
                "dimension_progress": _get_dimension_progress(session),
            }
            req_log.flush(result)
            return result

        session.current_dimension = DIMENSIONS[current_idx + 1]
        rebuilt = []
        for dim_key in DIMENSIONS:
            if dim_key in session.dimension_summaries:
                dim_label = DIMENSION_LABELS.get(dim_key, dim_key)
                rebuilt.append(Message(
                    role="assistant",
                    content=f"{dim_label}维度总结：{session.dimension_summaries[dim_key]}",
                ))
        session.messages = rebuilt
        session.dimension_message_start = len(rebuilt)

    # ── Node 3: Dialogue ──
    try:
        question = await _run_dialogue_node(session, request_id, req_log)
    except Exception:
        logger.exception("[DIALOGUE] Error")
        req_log.flush({"code": "internal_error", "message": "对话服务暂时不可用，请重试"})
        return {"code": "internal_error", "message": "对话服务暂时不可用，请重试"}

    if not question:
        req_log.flush({"code": "parse_error", "message": "AI返回为空，请重试"})
        return {"code": "parse_error", "message": "AI返回为空，请重试"}

    # ── Node 4: Option Generation ──
    options = None
    try:
        options = await _run_option_node(question, request_id, req_log)
    except Exception:
        logger.exception("[OPTIONS] Error, proceeding without options")

    design_complete = len(session.completed_dimensions) >= len(DIMENSIONS)
    dialogue_complete = design_complete

    result = {
        "content": question,
        "options": options,
        "design_complete": design_complete,
        "dialogue_complete": dialogue_complete,
        "dimension_progress": _get_dimension_progress(session),
    }
    req_log.flush(result)
    return result
