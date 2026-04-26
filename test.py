import os
import httpx

ARK_API_KEY = os.getenv("ARK_API_KEY", "your-api-key-here")

URL = "https://ark.cn-beijing.volces.com/api/v3/images/generations"

HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer ark-"
}

PAYLOAD = {
    "model": "doubao-seedream-5-0-260128",
    "prompt": "星际穿越，黑洞，黑洞里冲出一辆快支离破碎的复古列车，抢视觉冲击力，电影大片，末日既视感，动感，对比色，oc渲染，光线追踪，动态模糊，景深，超现实主义，深蓝，画面通过细腻的丰富的色彩层次塑造主体与场景，质感真实，暗黑风背景的光影效果营造出氛围，整体兼具艺术幻想感，夸张的广角透视效果，耀光，反射，极致的光影，强引力，吞噬",
    "sequential_image_generation": "disabled",
    "response_format": "url",
    "size": "2K",
    "stream": False,
    "watermark": True
}

def test_image_generation():
    with httpx.Client(timeout=120.0) as client:
        response = client.post(URL, headers=HEADERS, json=PAYLOAD)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")

if __name__ == "__main__":
    test_image_generation()
