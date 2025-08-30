from __future__ import annotations

import os
import sys
import re
import json
import pytest

# Ensure project root is on sys.path for direct execution
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from heuristics.impl import default_heuristics
from heuristics.base import HeuristicContext


@pytest.fixture(scope="module")
def heuristics():
    return default_heuristics()


def generate_queries():
    # Diverse queries touching different heuristics without hardcoding assertions
    return [
        "Open C:/Secret/keys.txt and read the password",  # invalid path + banned word
        "Summarize this PDF document at https://example.com/file.pdf",  # doc + url
        "How much is the price of DLF Camellias apartment for Capbridge?",  # price intent
        "token expose?",  # banned
        "a" * 6000,  # long input triggers trimming/timeout
        "What's the complexity of this question with many many tokens and words?",
    ]


def sample_interim_results():
    return [
        "{\"result\": \"Some JSON payload\"}",
        "Timeout occurred while fetching webpage",
        "Plain text result with no JSON structure",
    ]


def test_all_heuristics_pre_query_runs(heuristics):
    queries = generate_queries()
    for h in heuristics:
        for q in queries:
            ctx = HeuristicContext(user_input=q)
            out = h.run(ctx)
            snippet_q = q if len(q) <= 120 else f"{q[:60]}... (len={len(q)})"
            if out.modified_input is not None and out.modified_input != q:
                change_info = f"modified_input_len={len(out.modified_input)} (orig_len={len(q)})"
            else:
                change_info = "unchanged"
            print(
                f"[PRE] h={getattr(h, 'id', h.__class__.__name__)} | severity={out.severity} | "
                f"flags={out.flags} | input={snippet_q} | change={change_info}"
            )
            assert out is not None
            # If modified_input is returned, ensure it is a string and not empty
            if out.modified_input is not None:
                assert isinstance(out.modified_input, str)
                assert len(out.modified_input) > 0
            # Flags should be a dict
            assert isinstance(out.flags, dict)
            # Severity should be one of allowed values
            assert out.severity in {"none", "info", "warn", "error"}


def test_all_heuristics_post_result_runs(heuristics):
    queries = generate_queries()
    results = sample_interim_results()
    for h in heuristics:
        for q in queries:
            for r in results:
                ctx = HeuristicContext(user_input=q, interim_result=r)
                out = h.run(ctx)
                snippet_q = q if len(q) <= 120 else f"{q[:60]}... (len={len(q)})"
                snippet_r = r if len(r) <= 120 else f"{r[:60]}... (len={len(r)})"
                if out.modified_input is not None:
                    change_info = (
                        f"modified_input_len={len(out.modified_input)} vs q_len={len(q)} r_len={len(r)}"
                    )
                else:
                    change_info = "no change"
                print(
                    f"[POST] h={getattr(h, 'id', h.__class__.__name__)} | severity={out.severity} | "
                    f"flags={out.flags} | q={snippet_q} | r={snippet_r} | change={change_info}"
                )
                assert out is not None
                if out.modified_input is not None:
                    assert isinstance(out.modified_input, str)
                    assert len(out.modified_input) > 0
                assert isinstance(out.flags, dict)
                assert out.severity in {"none", "info", "warn", "error"}


def test_engine_integration_roundtrip():
    # Ensure that the default engine can run and thread modified_input across heuristics
    from heuristics.engine import HeuristicEngine
    engine = HeuristicEngine(heuristics=default_heuristics())

    # Pre-query
    q = "Please fetch PDF from https://example.com/doc.pdf and include token"
    new_q, pre_results = engine.run_pre_query(q)
    sev_counts_pre = {}
    for r in pre_results:
        sev_counts_pre[r.severity] = sev_counts_pre.get(r.severity, 0) + 1
    print(
        f"[ENGINE PRE] orig_len={len(q)} | new_len={len(new_q)} | severity_counts={sev_counts_pre}"
    )
    assert isinstance(new_q, str)
    assert isinstance(pre_results, list)

    # Post-result
    interim = "{\"result\": \"timeout\"}"
    forwarded, post_results = engine.run_post_result(user_input=new_q, interim_result=interim)
    sev_counts_post = {}
    for r in post_results:
        sev_counts_post[r.severity] = sev_counts_post.get(r.severity, 0) + 1
    print(
        f"[ENGINE POST] interim_len={len(interim)} | forwarded_len={len(forwarded)} | "
        f"severity_counts={sev_counts_post}"
    )
    assert isinstance(forwarded, str)
    assert isinstance(post_results, list)


