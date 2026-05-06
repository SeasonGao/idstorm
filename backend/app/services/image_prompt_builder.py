"""Image prompt builder service.

Generates one composite prompt per candidate variant, combining
three-view and scene showcase into a single image with top-bottom layout.
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
    """Build N composite prompts (one per candidate) from the design requirement.

    Returns list of dicts:
        [{"candidate_id": "c1", "prompt": "..."}, ...]
    """

    product_name = requirement.product_name or "产品"
    three_view_desc = requirement.three_view_desc
    scene_desc = requirement.scene_desc

    # Fallback: synthesize from dimension fields if descriptions are empty
    if not three_view_desc or not scene_desc:
        fields: dict[str, str] = {}
        for dim in requirement.dimensions:
            for f in dim.fields:
                fields[f.key] = f.value
        if not three_view_desc:
            three_view_desc = _fallback_three_view(fields)
        if not scene_desc:
            scene_desc = _fallback_scene(fields)

    # Get variant modifiers from DeepSeek
    variants = await _suggest_variants(product_name, three_view_desc, scene_desc, count, api_keys)

    prompts: list[dict] = []
    for variant in variants:
        modifier = variant.get("modifier", "")
        prompt = _build_composite_prompt(product_name, three_view_desc, scene_desc, modifier)
        prompts.append({
            "candidate_id": variant["id"],
            "prompt": prompt,
        })

    return prompts


def _build_composite_prompt(
    product_name: str,
    three_view_desc: str,
    scene_desc: str,
    modifier: str,
) -> str:
    """Build a single composite prompt for top-bottom layout image."""
    modifier_part = f"\n{modifier}。" if modifier else ""
    return (
        f'生成以下两张关于"{product_name}"的图片，通过上下结构排版。'
        f'两张图片描述的"{product_name}"必须保持一致性：\n'
        f'\n'
        f'图片一："{product_name}"的三视图，包含正视图、侧视图、俯视图，'
        f"背景为干净的纯白色。{three_view_desc}{modifier_part}\n"
        f'\n'
        f'图片二："{product_name}"的展示图，{scene_desc}{modifier_part}'
    )


def _fallback_three_view(fields: dict) -> str:
    parts = []
    if fields.get("form_size"):
        parts.append(fields["form_size"])
    if fields.get("material_color"):
        parts.append(fields["material_color"])
    return "，".join(parts) if parts else "产品渲染风格，柔和影棚灯光，高分辨率，背景无阴影，技术绘图美学"


def _fallback_scene(fields: dict) -> str:
    parts = []
    if fields.get("scenario"):
        parts.append(fields["scenario"])
    if fields.get("brand"):
        parts.append(fields["brand"])
    return "，".join(parts) if parts else "专业产品摄影风格，柔和自然光，浅景深，高清画质"


async def _suggest_variants(
    product_name: str,
    three_view_desc: str,
    scene_desc: str,
    count: int = 3,
    api_keys: dict | None = None,
) -> list[dict]:
    """Ask DeepSeek to suggest N micro-variant modifiers."""
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    examples = "\n".join(
        f'  {{"id": "c{i+1}", "label": "方案{letters[i]}", "modifier": "示例修饰语{i+1}"}}'
        + ("," if i < min(count, 3) - 1 else "")
        for i in range(min(count, 3))
    )

    variant_prompt = f"""基于以下产品设计描述，建议{count}个微调变种方案。每个变种保持核心设计不变，只在一个次要属性上有细微差异（如色彩微调、材质细节变化、造型微调等）。

产品名称：{product_name}
三视图描述：{three_view_desc[:300]}
场景描述：{scene_desc[:300]}

输出JSON数组格式：
[
{examples}
]

只输出JSON数组，不要其他文字。确保{count}个变种的modifier描述简洁（20字以内），且保持微调而非大改。每个modifier应该同时适用于三视图和场景展示图。"""

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
        fallback_modifiers = ["标准设计", "色彩微调，质感变化", "细节调整，功能元素", "形态简化，材质混合", "大胆配色，造型突破"]
        return [
            {"id": f"c{i+1}", "label": f"方案{letters[i]}", "modifier": fallback_modifiers[i % len(fallback_modifiers)]}
            for i in range(count)
        ]
