from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from app.models.requirement import DesignRequirement


@dataclass
class Session:
    id: str
    initial_idea: str
    status: str = "dialogue"  # "dialogue" | "requirement" | "generating" | "review"
    created_at: datetime = field(default_factory=datetime.now)
    messages: list = field(default_factory=list)
    requirement: Optional[DesignRequirement] = None
    candidates: Optional[list] = None
    current_dimension: str = "form_size"
    completed_dimensions: list = field(default_factory=list)
