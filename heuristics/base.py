from __future__ import annotations

from typing import Any, Dict, Optional
from pydantic import BaseModel


class HeuristicContext(BaseModel):
    """Carries inputs and side-channel info for heuristics.

    - user_input: The incoming query text
    - interim_result: Latest tool output or forwarded content, if any
    - metadata: Arbitrary context (e.g., session id, step)
    """

    user_input: str
    interim_result: Optional[str] = None
    metadata: Dict[str, Any] = {}


class HeuristicResult(BaseModel):
    """Standardized output of a heuristic.

    - modified_input: Optional new user_input
    - notes: Short description of what was changed or detected
    - flags: Machine-readable flags (e.g., {"banned_terms_found": True})
    - severity: none|info|warn|error
    """

    modified_input: Optional[str] = None
    notes: Optional[str] = None
    flags: Dict[str, Any] = {}
    severity: str = "none"


class Heuristic(BaseModel):
    id: str
    description: str
    enabled: bool = True

    def run(self, ctx: HeuristicContext) -> HeuristicResult:  # pragma: no cover - interface only
        raise NotImplementedError


