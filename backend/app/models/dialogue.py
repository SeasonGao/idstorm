from dataclasses import dataclass
from datetime import datetime


@dataclass
class Message:
    role: str  # "user" | "assistant" | "system"
    content: str
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
