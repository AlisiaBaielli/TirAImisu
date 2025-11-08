from dataclasses import dataclass, asdict
from typing import Dict, Any


@dataclass
class Medication:
    """
    Canonical Medication entity used across the backend.
    """
    id: str
    name: str
    time: int  # Hour of day (0-23)
    color: str  # UI color token, e.g. "med-blue"
    hour_interval: int
    description: str | None = None


    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


