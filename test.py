import os
import httpx
ARK_API_KEY = ""

URL = "https://ark.cn-beijing.volces.com/api/v3/images/generations"

HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {ARK_API_KEY}"
}

PAYLOAD = {
    "model": "doubao-seedream-5-0-260128",
    "prompt": """生成以下两张关于“电热水壶”的图片，通过上下结构排版。两张图片描述的“电热水壶”必须保持一致性：
图片一：电热水壶的三视图，包含正视图、侧视图、俯视图，背景为干净的纯白色。薄木底座，极薄造型，现代极简风格的水壶主体，采用哑光白色塑料和透明玻璃或磨砂玻璃。仅底座带有木纹，浅橡木色。线条简洁流畅，年轻化设计，吸引年轻上班族。无多余装饰。产品渲染风格，柔和影棚灯光，高分辨率，背景无阴影，技术绘图美学。

图片二：电热水壶的展示图，一款面向年轻职场人士的现代电热水壶，配有纤薄的浅橡木色木底座（浅橡木），底座极低，水壶主体为哑光暖白色，带有细腻的透明玻璃窗或全半透明壶身，极简和谐设计。放置在明亮家庭办公室的浅木色书桌上，旁边有一台笔记本电脑和一盆植物。柔和的自然光，温馨干净的视觉效果。年轻、都市、有品味。产品摄影风格，浅景深，8K，电影感画面。""",
    "sequential_image_generation": "disabled",
    "response_format": "url",
    "size": "2K",
    "stream": False,
    "watermark": False
}

def test_image_generation():
    with httpx.Client(timeout=120.0) as client:
        response = client.post(URL, headers=HEADERS, json=PAYLOAD)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")

if __name__ == "__main__":
    test_image_generation()
