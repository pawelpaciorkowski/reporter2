from dataclasses import dataclass
from typing import Optional, List, Dict, Any


@dataclass(frozen=True)
class ApiAccessTokenData:
    sub: str
    endpoints: List[str]
    settings: Dict[str, Any]
