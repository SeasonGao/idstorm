import os

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    deepseek_api_key: str = ""
    openai_api_key: str = ""
    deepseek_model: str = "deepseek-v4-flash"
    deepseek_base_url: str = "https://api.deepseek.com"
    image_size: str = "1024x1024"
    image_concurrency: int = 6
    max_dialogue_rounds: int = 8
    # Doubao Seedream (default image model)
    doubao_api_key: str = ""
    doubao_base_url: str = "https://ark.cn-beijing.volces.com/api/v3"
    doubao_model: str = "doubao-seedream-5-0-260128"
    doubao_image_size: str = "2K"
    # Default image provider: "doubao" or "openai"
    default_image_provider: str = "doubao"

    class Config:
        env_file = ".env"


settings = Settings()

IMAGES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".generated_images")
