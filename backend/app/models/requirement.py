from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DimensionField:
    key: str
    label: str
    value: str
    editable: bool = True


@dataclass
class Dimension:
    key: str
    label: str
    fields: list[DimensionField] = field(default_factory=list)


@dataclass
class DesignRequirement:
    dimensions: list[Dimension] = field(default_factory=list)
    version: int = 1
