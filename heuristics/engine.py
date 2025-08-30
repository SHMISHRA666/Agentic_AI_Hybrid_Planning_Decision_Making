from __future__ import annotations

from typing import List, Iterable
from pydantic import BaseModel

from .base import Heuristic, HeuristicContext, HeuristicResult


class HeuristicEngine(BaseModel):
    """Runs a pipeline of heuristics over a query and/or results."""

    heuristics: List[Heuristic] = []

    def run_pre_query(self, user_input: str, metadata: dict | None = None) -> tuple[str, list[HeuristicResult]]:
        ctx = HeuristicContext(user_input=user_input, interim_result=None, metadata=metadata or {})
        return self._run(ctx)

    def run_post_result(self, user_input: str, interim_result: str, metadata: dict | None = None) -> tuple[str, list[HeuristicResult]]:
        ctx = HeuristicContext(user_input=user_input, interim_result=interim_result, metadata=metadata or {})
        return self._run(ctx)

    def _run(self, ctx: HeuristicContext) -> tuple[str, list[HeuristicResult]]:
        results: list[HeuristicResult] = []
        # For post-result flows, prefer interim_result as the working text; fallback to user_input
        current_input = ctx.interim_result if ctx.interim_result is not None else ctx.user_input

        for h in self._enabled(self.heuristics):
            try:
                r = h.run(HeuristicContext(user_input=current_input, interim_result=ctx.interim_result, metadata=ctx.metadata))
            except Exception as e:  # never break the pipeline on heuristic failures
                r = HeuristicResult(notes=f"heuristic_error: {h.id}: {e}", severity="warn")

            if r.modified_input is not None:
                current_input = r.modified_input
            results.append(r)

        return current_input, results

    @staticmethod
    def _enabled(heuristics: Iterable[Heuristic]) -> Iterable[Heuristic]:
        for h in heuristics:
            if getattr(h, "enabled", True):
                yield h


