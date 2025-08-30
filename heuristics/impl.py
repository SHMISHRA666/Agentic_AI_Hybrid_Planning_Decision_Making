from __future__ import annotations

import re
import json
from typing import List
from pydantic import Field

from .base import Heuristic, HeuristicContext, HeuristicResult


class InvalidFileDetector(Heuristic):
    id: str = "invalid_file_detector"
    description: str = "Validate file existence patterns and reject unsupported paths."

    def run(self, ctx: HeuristicContext) -> HeuristicResult:
        # Simple heuristic: warn if Windows path with illegal characters or likely non-existent drive
        flags = {}
        notes = None
        match = re.search(r"([A-Za-z]):\\", ctx.user_input)
        if match and match.group(1).lower() not in list("cdefghijklmno"):  # heuristic only
            notes = "Suspicious drive letter detected in query"
            flags["suspicious_path"] = True
        return HeuristicResult(modified_input=None, notes=notes, flags=flags, severity="info" if notes else "none")


class InputValidationSystem(Heuristic):
    id: str = "input_validation_system"
    description: str = "Validate structure and basic constraints for inputs."

    min_len: int = Field(1, ge=0)
    max_len: int = Field(10000, ge=1)

    def run(self, ctx: HeuristicContext) -> HeuristicResult:
        text = ctx.user_input or ""
        if len(text) < self.min_len:
            return HeuristicResult(notes="input_too_short", severity="error")
        if len(text) > self.max_len:
            trimmed = text[: self.max_len]
            return HeuristicResult(modified_input=trimmed, notes="input_trimmed", flags={"original_length": len(text)}, severity="warn")
        return HeuristicResult()


class BannedWordsFilter(Heuristic):
    id: str = "banned_words_filter"
    description: str = "Filter and mask banned words from the query."

    banned: List[str] = ["password", "apikey", "token"]

    def run(self, ctx: HeuristicContext) -> HeuristicResult:
        text = ctx.user_input
        masked = text
        found = []
        for w in self.banned:
            pattern = re.compile(re.escape(w), re.IGNORECASE)
            if pattern.search(text):
                found.append(w)
                masked = pattern.sub("[REDACTED]", masked)
        if found:
            return HeuristicResult(modified_input=masked, notes=f"banned_terms_masked: {found}", flags={"banned_terms_found": found}, severity="warn")
        return HeuristicResult()


class QueryComplexityAnalyzer(Heuristic):
    id: str = "query_complexity_analyzer"
    description: str = "Estimate query complexity via token-like heuristics."

    def run(self, ctx: HeuristicContext) -> HeuristicResult:
        tokens = re.findall(r"\w+", ctx.user_input)
        complexity = len(tokens)
        flag = {"complexity_score": complexity}
        return HeuristicResult(notes=f"complexity_score={complexity}", flags=flag, severity="info")


class ToolUsageOptimizer(Heuristic):
    id: str = "tool_usage_optimizer"
    description: str = "Hint tool selection: prefer web/doc tools when query mentions URLs/docs."

    def run(self, ctx: HeuristicContext) -> HeuristicResult:
        text = ctx.user_input.lower()
        flags = {}
        if "http://" in text or "https://" in text:
            flags["prefer_web_tools"] = True
        if any(x in text for x in ["pdf", "document", "doc", "paper"]):
            flags["prefer_document_tools"] = True
        return HeuristicResult(flags=flags, severity="info")


class ErrorPatternDetector(Heuristic):
    id: str = "error_pattern_detector"
    description: str = "Detect common error patterns in interim results and suggest retry."

    def run(self, ctx: HeuristicContext) -> HeuristicResult:
        if not ctx.interim_result:
            return HeuristicResult()
        text = ctx.interim_result.lower()
        retry = any(err in text for err in ["timeout", "rate limit", "exceeded max tool calls"])
        return HeuristicResult(flags={"retry_suggested": retry} if retry else {}, severity="warn" if retry else "none")


class ResponseFormatValidator(Heuristic):
    id: str = "response_format_validator"
    description: str = "Ensure interim result can be parsed; if JSON-like, validate minimal structure."

    def run(self, ctx: HeuristicContext) -> HeuristicResult:
        if not ctx.interim_result:
            return HeuristicResult()
        text = ctx.interim_result.strip()
        if text.startswith("{") and text.endswith("}"):
            try:
                json.loads(text)
                return HeuristicResult(notes="json_parse_ok", severity="info")
            except Exception:
                return HeuristicResult(notes="json_parse_failed", severity="warn")
        return HeuristicResult()


class HistoricalPatternRecognizer(Heuristic):
    id: str = "historical_pattern_recognizer"
    description: str = "Surface that past runs with similar wording were successful."

    def run(self, ctx: HeuristicContext) -> HeuristicResult:
        # Placeholder: in a real impl, consult memory index
        hint = "similar_past_query_found"
        return HeuristicResult(notes=hint, flags={hint: False}, severity="info")


class TimeoutManager(Heuristic):
    id: str = "timeout_manager"
    description: str = "Raise urgency/severity if long content with web/doc hints."

    def run(self, ctx: HeuristicContext) -> HeuristicResult:
        long_text = len(ctx.user_input) > 2000
        if long_text:
            return HeuristicResult(notes="long_input_detected", flags={"suggest_shorter_timeout": True}, severity="info")
        return HeuristicResult()


class QueryIntentMatcher(Heuristic):
    id: str = "query_intent_matcher"
    description: str = "Extract simple intents from the query using regex rules."

    def run(self, ctx: HeuristicContext) -> HeuristicResult:
        text = ctx.user_input.lower()
        intent = None
        if any(k in text for k in ["price", "cost", "how much"]):
            intent = "ask_price"
        elif any(k in text for k in ["who", "person", "name"]):
            intent = "ask_person"
        if intent:
            return HeuristicResult(flags={"intent": intent}, severity="info")
        return HeuristicResult()


# Export a default set of 10 heuristics
def default_heuristics() -> list[Heuristic]:
    return [
        InvalidFileDetector(),
        InputValidationSystem(),
        BannedWordsFilter(),
        QueryComplexityAnalyzer(),
        ToolUsageOptimizer(),
        ErrorPatternDetector(),
        ResponseFormatValidator(),
        HistoricalPatternRecognizer(),
        TimeoutManager(),
        QueryIntentMatcher(),
    ]


