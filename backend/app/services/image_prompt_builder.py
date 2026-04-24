"""Image prompt builder service for generating detailed image generation prompts.

Constructs prompts from structured design requirements, producing
orthographic and render-style prompts for each candidate variant.
"""

import json
import logging

import httpx

from app.config import settings
from app.models.requirement import DesignRequirement

logger = logging.getLogger(__name__)


async def build_image_prompts(requirement: DesignRequirement) -> list[dict]:
    """Build 6 image prompts (3 candidates x 2 views) from the design requirement.

    Returns list of 6 dicts:
        [{"candidate_id": "c1", "view": "orthographic", "prompt": "..."}, ...]
    """

    # Extract fields into a flat dict
    fields: dict[str, str] = {}
    for dim in requirement.dimensions:
        for f in dim.fields:
            fields[f.key] = f.value

    # Get variant suggestions from DeepSeek
    variants = await _suggest_variants(fields)

    prompts: list[dict] = []
    for variant in variants:
        # Orthographic view prompt
        ortho_prompt = (
            f"技术三视图（正视图、侧视图、俯视图排列在同一画布上）"
            f"的一个{fields.get('morphology', '产品')}产品。"
            f"风格：干净的线条绘制，{fields.get('line_style', '简约')}，白色背景上的技术插图。"
            f"尺寸比例：{fields.get('proportions', '适中')}。"
            f"材质标示：{fields.get('material', '未指定')}，{fields.get('surface_treatment', '标准处理')}。"
            f"主色调：{fields.get('color_palette', '中性色')}。"
            f"变体：{variant['modifier']}。"
            f"无背景、无人物、无环境。纯技术绘图风格。"
        )

        # Showcase render prompt
        render_prompt = (
            f"逼真的产品摄影照，{fields.get('morphology', '产品')}产品。"
            f"{variant['modifier']}。"
            f"材质：{fields.get('material', '未指定')}，{fields.get('surface_treatment', '标准处理')}。"
            f"色彩：{fields.get('color_palette', '中性色')}。"
            f"场景：{fields.get('usage_context', '日常使用')}，专业影棚灯光。"
            f"目标市场：{fields.get('target_audience', '大众消费者')}。品牌感：{fields.get('brand_tone', '现代简约')}。"
            f"白色/浅灰渐变影棚背景，专业产品摄影，浅景深，高清画质。"
        )

        prompts.append({
            "candidate_id": variant["id"],
            "view": "orthographic",
            "prompt": ortho_prompt,
        })
        prompts.append({
            "candidate_id": variant["id"],
            "view": "render",
            "prompt": render_prompt,
        })

    return prompts


async def _suggest_variants(fields: dict) -> list[dict]:
    """Ask DeepSeek to suggest 3 micro-variants."""

    variant_prompt = f"""基于以下设计需求，建议3个微调变种方案。每个变种保持核心风格不变，只在一个次要属性上有差异。

设计需求：
- 形态：{fields.get('morphology', '')}
- 比例：{fields.get('proportions', '')}
- 材质：{fields.get('material', '')}
- 色彩：{fields.get('color_palette', '')}

输出JSON数组格式：
[
  {{"id": "c1", "label": "方案A", "modifier": "标准设计，温暖木质细节"}},
  {{"id": "c2", "label": "方案B", "modifier": "略微冷色调，金属质感加强"}},
  {{"id": "c3", "label": "方案C", "modifier": "添加功能性元素，表面纹理变化"}}
]

只输出JSON数组，不要其他文字。确保3个变种的modifier描述简洁（15字以内），且保持微调而非大改。"""

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{settings.deepseek_base_url}/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.deepseek_api_key}"},
                json={
                    "model": settings.deepseek_model,
                    "messages": [{"role": "user", "content": variant_prompt}],
                    "temperature": 0.7,
                },
            )
            response.raise_for_status()
            result = response.json()
            content = result["choices"][0]["message"]["content"].strip()

            # Parse JSON — strip markdown code fences if present
            if content.startswith("```"):
                content = content.split("\n", 1)[1] if "\n" in content else content[3:]
                if content.endswith("```"):
                    content = content[:-3]
                content = content.strip()

            return json.loads(content)
    except Exception:
        logger.warning("Variant suggestion failed, using fallback variants")
        return [
            {"id": "c1", "label": "方案A", "modifier": "标准设计"},
            {"id": "c2", "label": "方案B", "modifier": "色彩微调，质感变化"},
            {"id": "c3", "label": "方案C", "modifier": "细节调整，功能元素"},
        ]
