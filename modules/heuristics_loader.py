from __future__ import annotations

import yaml
from typing import List

from heuristics.engine import HeuristicEngine
from heuristics.impl import (
    InvalidFileDetector,
    InputValidationSystem,
    BannedWordsFilter,
    QueryComplexityAnalyzer,
    ToolUsageOptimizer,
    ErrorPatternDetector,
    ResponseFormatValidator,
    HistoricalPatternRecognizer,
    TimeoutManager,
    QueryIntentMatcher,
    default_heuristics,
)


ID_TO_CLASS = {
    "invalid_file_detector": InvalidFileDetector,
    "input_validation_system": InputValidationSystem,
    "banned_words_filter": BannedWordsFilter,
    "query_complexity_analyzer": QueryComplexityAnalyzer,
    "tool_usage_optimizer": ToolUsageOptimizer,
    "error_pattern_detector": ErrorPatternDetector,
    "response_format_validator": ResponseFormatValidator,
    "historical_pattern_recognizer": HistoricalPatternRecognizer,
    "timeout_manager": TimeoutManager,
    "query_intent_matcher": QueryIntentMatcher,
}


def load_engine_from_config(path: str = "config/heuristics.yaml") -> HeuristicEngine:
    try:
        with open(path, "r") as f:
            data = yaml.safe_load(f)
    except Exception:
        return HeuristicEngine(heuristics=default_heuristics())

    if not data or not data.get("enabled", True):
        return HeuristicEngine(heuristics=[])

    pre = data.get("pre_query", [])
    post = data.get("post_result", [])

    heuristics = []
    for section in (pre + post):
        if not section.get("enabled", True):
            continue
        hid = section.get("id")
        cls = ID_TO_CLASS.get(hid)
        if cls is None:
            continue
        params = {k: v for k, v in section.items() if k not in {"id", "enabled"}}
        heuristics.append(cls(**params))

    if not heuristics:
        heuristics = default_heuristics()

    return HeuristicEngine(heuristics=heuristics)


