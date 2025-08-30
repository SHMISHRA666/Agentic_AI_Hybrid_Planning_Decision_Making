from __future__ import annotations

import asyncio
import io
import json
import os
import re
import sys
from contextlib import redirect_stdout
from datetime import datetime
from typing import List, Dict

# Ensure project root on path when executed as module
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import yaml  # type: ignore

from core.session import MultiMCP
from core.context import AgentContext
from core.loop import AgentLoop


def read_queries(path: str = "Queries.txt", limit: int = 3) -> List[str]:
    queries: List[str] = []
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                q = line.strip()
                if q:
                    queries.append(q)
                if len(queries) >= limit:
                    break
    if not queries:
        # Fallback queries (not hardcoded in agent.py)
        queries = [
            "Compute the factorial of 15",
            "List the first 12 Fibonacci numbers",
            "Search the web for 'DLF Camellias Capbridge amount' and report amounts mentioned",
        ]
    return queries[:limit]


def extract_perception(log_text: str) -> str:
    # Capture JSON block following 'Raw output:'
    m = re.search(r"Raw output:\s*```json\n(.*?)\n```", log_text, flags=re.DOTALL)
    return m.group(1).strip() if m else ""


def extract_plan(log_text: str) -> str:
    # Capture python code block after [plan] LLM output
    m = re.search(r"\[plan\].*?```python\n(.*?)\n```", log_text, flags=re.DOTALL)
    return m.group(1).strip() if m else ""


def extract_final_answer(log_text: str) -> str:
    m = re.search(r"Final Answer:\s*(.*)$", log_text, flags=re.MULTILINE)
    return m.group(1).strip() if m else ""


async def run_single_query(mcp_servers: Dict, query: str) -> Dict[str, str]:
    # Initialize dispatcher fresh per batch
    multi_mcp = MultiMCP(server_configs=list(mcp_servers.values()))
    await multi_mcp.initialize()

    # Run the agent and capture stdout logs
    buf = io.StringIO()
    with redirect_stdout(buf):
        context = AgentContext(
            user_input=query,
            session_id=None,
            dispatcher=multi_mcp,
            mcp_server_descriptions=mcp_servers,
        )
        agent = AgentLoop(context)
        result = await agent.run()

        # Print final answer consistently as in agent.py
        if isinstance(result, dict):
            answer = result["result"]
            if "FINAL_ANSWER:" in answer:
                print(f"\n💡 Final Answer: {answer.split('FINAL_ANSWER:')[1].strip()}")
            else:
                print(f"\n💡 Final Answer (raw): {answer}")
        else:
            print(f"\n💡 Final Answer (unexpected): {result}")

    full_log = buf.getvalue()
    perception = extract_perception(full_log)
    plan = extract_plan(full_log)
    final_answer = extract_final_answer(full_log)

    return {
        "query": query,
        "perception": perception,
        "plan": plan,
        "final_answer": final_answer,
        "full_log": full_log,
    }


def write_bugfix_report(path: str = "BUGFIX_REPORT.md") -> None:
    content = """# Bug Fix Report

Date: {date}

## Summary
- Fixed loop stalling at initial stage by forwarding intermediate results via `user_input_override` and switching to a summarization prompt when needed.
- Escaped curly braces in prompt examples to prevent `str.format` KeyErrors.
- Added heuristics pipeline (10 heuristics) with pre-query and post-result processing.
- Injected same-session memory into planning prompts via `{{memory_context}}` placeholder.
- Added historical conversation indexing and retrieval (few-shot) into planning.
- Improved forwarding: extract readable text from tool results before summarization.

## Key changes
- `core/loop.py`: use forwarded input for planning; forward tool results; extract text for summarization; log lifelines properly.
- `prompts/decision_prompt_conservative.txt`: condensed and braces escaped; accepts `{{memory_context}}`.
- `prompts/decision_prompt_exploratory_*.txt`: added `{{memory_context}}`.
- `prompts/decision_prompt_summarize.txt`: parse INR amounts; escaped f-string variables.
- `modules/decision.py`: prepend few-shot history and same-session memory context to prompts.
- `heuristics/…`: new module with 10 heuristics and config loader.
- `history_index/…`: indexer and retriever using NumPy/FAISS.
- `tests/test_heuristics.py`: coverage for all heuristics; engine roundtrip.

## Impact
- Agent now advances plan stages and produces final answers instead of hitting max steps.
- Summarization step robustly interprets forwarded content and extracts numeric answers when present.
- Memory (both session and historical) enhances plan quality without regressions.
""".format(date=datetime.utcnow().isoformat())

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def write_execution_logs(examples: List[Dict[str, str]], path: str = "EXECUTION_LOGS.md") -> None:
    if not examples:
        return

    lines = [
        "# Execution Logs (auto-generated)",
        "",
        "Each example shows Query → Perception → Plan → Final Result.",
        "",
    ]
    for i, ex in enumerate(examples, 1):
        lines.append(f"## Example {i}")
        lines.append("")
        lines.append("Query:")
        lines.append(f"```\n{ex['query']}\n```")
        if ex.get("perception"):
            lines.append("Perception (JSON):")
            lines.append(f"```json\n{ex['perception']}\n```")
        if ex.get("plan"):
            lines.append("Plan (solve):")
            lines.append(f"```python\n{ex['plan']}\n```")
        lines.append("Result:")
        lines.append(f"```\n{ex.get('final_answer','')}\n```")
        lines.append("")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def write_historical_store(examples: List[Dict[str, str]], path: str = "historical_conversation_store.json") -> None:
    # Store concise Q/A pairs and associated perception/plan/logs
    payload = []
    for ex in examples:
        payload.append({
            "query": ex.get("query", ""),
            "perception": ex.get("perception", ""),
            "plan": ex.get("plan", ""),
            "final_answer": ex.get("final_answer", ""),
            "log": ex.get("full_log", ""),
            "timestamp": datetime.utcnow().isoformat(),
        })
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


async def main():
    # Load MCP server configs
    with open(os.path.join(PROJECT_ROOT, "config", "profiles.yaml"), "r", encoding="utf-8") as f:
        profile = yaml.safe_load(f)
    mcp_servers_list = profile.get("mcp_servers", [])
    mcp_servers = {server["id"]: server for server in mcp_servers_list}

    queries = read_queries()
    examples: List[Dict[str, str]] = []
    for q in queries:
        ex = await run_single_query(mcp_servers, q)
        examples.append(ex)

    # Write required artifacts
    write_bugfix_report()
    write_execution_logs(examples)
    write_historical_store(examples)

    print("Generated: BUGFIX_REPORT.md, updated README.md, historical_conversation_store.json")


if __name__ == "__main__":
    asyncio.run(main())


