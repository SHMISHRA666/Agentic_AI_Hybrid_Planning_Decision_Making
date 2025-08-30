# Bug Fix Report

Date: 2025-08-30T15:38:46.867237

## Summary
- Fixed loop stalling at initial stage by forwarding intermediate results via `user_input_override` and switching to a summarization prompt when needed.
- Escaped curly braces in prompt examples to prevent `str.format` KeyErrors.
- Added heuristics pipeline (10 heuristics) with pre-query and post-result processing.
- Injected same-session memory into planning prompts via `{memory_context}` placeholder.
- Added historical conversation indexing and retrieval (few-shot) into planning.
- Improved forwarding: extract readable text from tool results before summarization.

## Key changes
- `core/loop.py`: use forwarded input for planning; forward tool results; extract text for summarization; log lifelines properly.
- `prompts/decision_prompt_conservative.txt`: condensed and braces escaped; accepts `{memory_context}`.
- `prompts/decision_prompt_exploratory_*.txt`: added `{memory_context}`.
- `prompts/decision_prompt_summarize.txt`: parse INR amounts; escaped f-string variables.
- `modules/decision.py`: prepend few-shot history and same-session memory context to prompts.
- `heuristics/…`: new module with 10 heuristics and config loader.
- `history_index/…`: indexer and retriever using NumPy/FAISS.
- `tests/test_heuristics.py`: coverage for all heuristics; engine roundtrip.

## Impact
- Agent now advances plan stages and produces final answers instead of hitting max steps.
- Summarization step robustly interprets forwarded content and extracts numeric answers when present.
- Memory (both session and historical) enhances plan quality without regressions.
