from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Message:
    role: str  # "user" | "assistant" | "system"
    content: str
    timestamp: datetime = None
    options: Optional[list[str]] = None
    hidden: bool = False

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
