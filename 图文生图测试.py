import os
import base64
import httpx
ARK_API_KEY = ""

URL = "https://ark.cn-beijing.volces.com/api/v3/images/generations"

HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {ARK_API_KEY}"
}

IMAGE_PATH = r"C:\Users\82444\Desktop\AIStory\idstorm\testimage.jpeg"

def test_image_generation():
    with open(IMAGE_PATH, "rb") as f:
        image_base64 = base64.b64encode(f.read()).decode("utf-8")
    image_data_uri = f"data:image/png;base64,{image_base64}"

    payload = {
        "model": "doubao-seedream-5-0-260128",
        "prompt": "把水壶的颜色改为黑色",
        "image": image_data_uri,
        "size": "2K",
        "output_format": "png",
        "watermark": False
    }

    with httpx.Client(timeout=120.0) as client:
        response = client.post(URL, headers=HEADERS, json=payload)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")

if __name__ == "__main__":
    test_image_generation()
