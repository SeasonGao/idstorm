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


async def build_image_prompts(
    requirement: DesignRequirement,
    count: int = 3,
    api_keys: dict | None = None,
) -> list[dict]:
    """Build image prompts (count candidates x 2 views) from the design requirement.

    Returns list of dicts:
        [{"candidate_id": "c1", "view": "orthographic", "prompt": "..."}, ...]
    """

    # Extract fields into a flat dict
    fields: dict[str, str] = {}
    for dim in requirement.dimensions:
        for f in dim.fields:
            fields[f.key] = f.value

    # Get variant suggestions from DeepSeek
    variants = await _suggest_variants(fields, count, api_keys)

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


async def _suggest_variants(fields: dict, count: int = 3, api_keys: dict | None = None) -> list[dict]:
    """Ask DeepSeek to suggest N micro-variants."""
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    examples = "\n".join(
        f'  {{"id": "c{i+1}", "label": "方案{letters[i]}", "modifier": "示例修饰语{i+1}"}}'
        + ("," if i < min(count, 3) - 1 else "")
        for i in range(min(count, 3))
    )

    variant_prompt = f"""基于以下设计需求，建议{count}个微调变种方案。每个变种保持核心风格不变，只在一个次要属性上有差异。

设计需求：
- 形态：{fields.get('morphology', '')}
- 比例：{fields.get('proportions', '')}
- 材质：{fields.get('material', '')}
- 色彩：{fields.get('color_palette', '')}

输出JSON数组格式：
[
{examples}
]

只输出JSON数组，不要其他文字。确保{count}个变种的modifier描述简洁（15字以内），且保持微调而非大改。"""

    api_key = (api_keys or {}).get("deepseek_api_key") or settings.deepseek_api_key

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{settings.deepseek_base_url}/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": settings.deepseek_model,
                    "messages": [{"role": "user", "content": variant_prompt}],
                    "temperature": 0.7,
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

            variants = json.loads(content)
            # Ensure we have the requested count
            if len(variants) < count:
                for i in range(len(variants), count):
                    variants.append({
                        "id": f"c{i+1}",
                        "label": f"方案{letters[i]}",
                        "modifier": f"变体{i+1}",
                    })
            return variants[:count]
    except Exception:
        logger.warning("Variant suggestion failed, using fallback variants")
        letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        fallback_modifiers = ["标准设计", "色彩微调，质感变化", "细节调整，功能元素", "形态简化，材质混合", "大胆配色，造型突破"]
        return [
            {"id": f"c{i+1}", "label": f"方案{letters[i]}", "modifier": fallback_modifiers[i % len(fallback_modifiers)]}
            for i in range(count)
        ]
