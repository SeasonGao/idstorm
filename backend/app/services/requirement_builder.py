"""Requirement builder service for constructing structured design requirements.

Transforms dialogue outputs into a structured DesignRequirement object
with dimensions (form size, material color, scenario, brand).
"""

import json
import logging

import httpx

from app.config import settings
from app.models.requirement import DimensionField, Dimension, DesignRequirement

logger = logging.getLogger(__name__)

EXTRACTION_SYSTEM_PROMPT = """你是一个设计需求分析专家。根据以下设计咨询对话，提取结构化的设计需求。

对于4个维度，根据用户的描述填写具体字段。如果某个字段没有被明确讨论，根据上下文推断合理的默认值。

输出JSON格式：
{
  "form_size": {
    "morphology": "产品形态描述",
    "proportions": "尺寸比例描述",
    "line_style": "线条风格描述"
  },
  "material_color": {
    "material": "主要材质",
    "surface_treatment": "表面处理",
    "color_palette": "色彩方案"
  },
  "scenario": {
    "usage_context": "使用场景",
    "interaction_method": "交互方式",
    "ergonomics": "人机工程"
  },
  "brand": {
    "brand_tone": "品牌调性",
    "price_range": "价格区间",
    "target_audience": "目标用户"
  }
}

只输出JSON，不要其他文字。"""

DIMENSION_CONFIGS = {
    "form_size": ("形态与尺寸", ["morphology", "proportions", "line_style"]),
    "material_color": ("材质与色彩", ["material", "surface_treatment", "color_palette"]),
    "scenario": ("使用场景与交互", ["usage_context", "interaction_method", "ergonomics"]),
    "brand": ("品牌与市场定位", ["brand_tone", "price_range", "target_audience"]),
}

FIELD_LABELS = {
    "morphology": "产品形态",
    "proportions": "尺寸比例",
    "line_style": "线条风格",
    "material": "主要材质",
    "surface_treatment": "表面处理",
    "color_palette": "色彩方案",
    "usage_context": "使用场景",
    "interaction_method": "交互方式",
    "ergonomics": "人机工程",
    "brand_tone": "品牌调性",
    "price_range": "价格区间",
    "target_audience": "目标用户",
}


def _strip_markdown_code_block(content: str) -> str:
    """Remove surrounding markdown code fences if present."""
    content = content.strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[1] if "\n" in content else content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
    return content


async def extract_requirement(messages: list) -> DesignRequirement:
    """Extract structured design requirement from dialogue history using DeepSeek."""

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
    for dim_key, (dim_label, field_keys) in DIMENSION_CONFIGS.items():
        dim_data = data.get(dim_key, {})
        fields: list[DimensionField] = []
        for fk in field_keys:
            fields.append(DimensionField(
                key=fk,
                label=FIELD_LABELS.get(fk, fk),
                value=dim_data.get(fk, "待定"),
                editable=True,
            ))
        dimensions.append(Dimension(key=dim_key, label=dim_label, fields=fields))

    return DesignRequirement(dimensions=dimensions, version=1)
