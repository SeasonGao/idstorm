import json
import logging

import httpx

from app.config import settings
from app.models.requirement import DimensionField, Dimension, DesignRequirement

logger = logging.getLogger(__name__)

EXTRACTION_SYSTEM_PROMPT = """你是一个设计需求提炼助手。根据以下设计咨询对话，提炼出4个维度的设计需求描述。

规则：
1. 只输出4个维度：形态与尺寸、材质与色彩、使用场景与交互、品牌与市场定位。
2. 每个维度只用一段话描述，把用户提到的相关信息合理串联起来。
3. 如果某个维度在对话中完全没有被讨论过，对应值填空字符串。
4. 不要推断或补充用户没有提到的信息。

输出JSON格式：
{
  "form_size": "一段关于产品形态和尺寸的描述",
  "material_color": "一段关于材质和色彩的描述",
  "scenario": "一段关于使用场景和交互方式的描述",
  "brand": "一段关于品牌调性和目标市场的描述"
}

只输出JSON，不要其他文字。"""

DIMENSION_CONFIGS = {
    "form_size": "形态与尺寸",
    "material_color": "材质与色彩",
    "scenario": "使用场景与交互",
    "brand": "品牌与市场定位",
}


def _strip_markdown_code_block(content: str) -> str:
    content = content.strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[1] if "\n" in content else content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
    return content


async def extract_requirement(messages: list) -> DesignRequirement:
    extraction_messages = [{"role": "system", "content": EXTRACTION_SYSTEM_PROMPT}]
    for msg in messages:
        if msg.role in ("user", "assistant"):
            extraction_messages.append({"role": msg.role, "content": msg.content})

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{settings.deepseek_base_url}/v1/chat/completions",
            headers={"Authorization": f"Bearer {settings.deepseek_api_key}"},
            json={
                "model": settings.deepseek_model,
                "messages": extraction_messages,
                "temperature": 0.1,
            },
        )
        response.raise_for_status()
        result = response.json()
        content = result["choices"][0]["message"]["content"]

    content = _strip_markdown_code_block(content)
    data = json.loads(content)

    dimensions: list[Dimension] = []
    for dim_key, dim_label in DIMENSION_CONFIGS.items():
        value = data.get(dim_key, "")
        dimensions.append(Dimension(
            key=dim_key,
            label=dim_label,
            fields=[DimensionField(
                key="description",
                label="需求描述",
                value=value,
                editable=True,
            )],
        ))

    return DesignRequirement(dimensions=dimensions, version=1)
