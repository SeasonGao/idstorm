from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CandidateImage:
    id: str
    image_type: str  # "orthographic" | "render"
    url: str
    prompt_used: str = ""


@dataclass
class Candidate:
    id: str
    label: str
    variant_description: str
    images: list[CandidateImage] = field(default_factory=list)
    iteration: int = 1
    status: str = "complete"  # "complete" | "partial"
    failed_views: list = field(default_factory=list)
