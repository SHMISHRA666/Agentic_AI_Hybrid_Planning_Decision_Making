from typing import List, Optional
from modules.perception import PerceptionResult
from modules.memory import MemoryItem
from modules.model_manager import ModelManager
from modules.tools import load_prompt
from history_index.retriever import HistoryRetriever
import re

# Optional logging fallback
try:
    from agent import log
except ImportError:
    import datetime
    def log(stage: str, msg: str):
        now = datetime.datetime.now().strftime("%H:%M:%S")
        print(f"[{now}] [{stage}] {msg}")

model = ModelManager()


# prompt_path = "prompts/decision_prompt.txt"

async def generate_plan(
    user_input: str, 
    perception: PerceptionResult,
    memory_items: List[MemoryItem],
    tool_descriptions: Optional[str],
    prompt_path: str,
    step_num: int = 1,
    max_steps: int = 5,
) -> str:

    """Generates the full solve() function plan for the agent."""

    # Build a concise same-session memory context (most recent first)
    recent = list(reversed(memory_items))[:8]
    memory_texts = "\n".join(f"- {m.text}" for m in recent) or "None"

    prompt_template = load_prompt(prompt_path)

    # Retrieve few-shot context from historical conversations
    try:
        retriever = HistoryRetriever()
        shots = retriever.retrieve(user_input, top_k=2)
        if shots:
            fewshot = "\n\n".join(
                [f"Q: {s.get('query','')}\nA: {s.get('answer','')}" for s in shots]
            )
            user_with_context = f"{fewshot}\n\nCurrent Task: {user_input}"
        else:
            user_with_context = user_input
    except Exception:
        user_with_context = user_input

    prompt = prompt_template.format(
        tool_descriptions=tool_descriptions,
        user_input=user_with_context,
        memory_context=memory_texts,
    )


    try:
        raw = (await model.generate_text(prompt)).strip()
        log("plan", f"LLM output: {raw}")

        # If fenced in ```python ... ```, extract
        if raw.startswith("```"):
            raw = raw.strip("`").strip()
            if raw.lower().startswith("python"):
                raw = raw[len("python"):].strip()

        if re.search(r"^\s*(async\s+)?def\s+solve\s*\(", raw, re.MULTILINE):
            return raw  # ✅ Correct, it's a full function
        else:
            log("plan", "⚠️ LLM did not return a valid solve(). Defaulting to FINAL_ANSWER")
            return "FINAL_ANSWER: [Could not generate valid solve()]"


    except Exception as e:
        log("plan", f"⚠️ Planning failed: {e}")
        return "FINAL_ANSWER: [unknown]"
