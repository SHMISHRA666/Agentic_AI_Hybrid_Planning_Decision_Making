### Agent Hybrid Planning & Decision Making (Cortex-R)

Reasoning-driven, tool-using agent that plans and executes actions across multiple MCP servers. It combines perception (intent/tool selection), planning (single or multi-step), execution (tool calls + sandboxed code), and persistent memory. Includes a local RAG pipeline over your `documents/` folder, web search/fetch tools, and math/utility tools.

---

### Features

- **Hybrid planning modes**: conservative (single function call) and exploratory (parallel or sequential fallbacks)
- **Multi-MCP orchestration**: discover and call tools from multiple MCP servers per task
- **Persistent memory**: per-session run metadata, tool I/O, and final answers under `memory/YYYY/MM/DD/`
- **Local RAG**: FAISS index built from `documents/` with semantic chunking and image captioning
- **Web tools**: DuckDuckGo search and raw webpage content extraction
- **Math & utilities**: arithmetic, trig, ASCII transforms, Fibonacci, thumbnails, etc.

---

### Requirements

- Python >= 3.11
- Recommended: `uv` (fast Python package manager). Fallback: `pip`
- For default text model (Gemini): set `GEMINI_API_KEY` in environment or `.env`
- For RAG and some image operations in `mcp_server_2.py` (optional but recommended): a running Ollama server providing
  - Embeddings endpoint (`/api/embeddings`) for model `nomic-embed-text`
  - Chat/generation endpoint (`/api/chat` or `/api/generate`) for models referenced in the server

Example Ollama setup (optional):

```bash
ollama serve
ollama pull nomic-embed-text
ollama pull phi4
ollama pull gemma3:12b
ollama pull qwen2.5:32b-instruct-q4_0
```

---

### Quickstart

1) Clone and enter the project directory.

2) Install dependencies

- Using uv (recommended):
```bash
uv sync
```

- Using pip (Windows PowerShell):
```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
```

- Using pip (macOS/Linux):
```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e .
```

3) Configure environment

- Create a `.env` file or export `GEMINI_API_KEY` if you use Gemini for planning/text (default):
```bash
GEMINI_API_KEY=your_api_key_here
```

4) Verify/adjust config paths

- Open `config/profiles.yaml` and update each `mcp_servers[*].cwd` to your local repo path if needed.
- Ensure `strategy` and `llm` settings are what you want (see below).

5) Run the agent

```bash
python agent.py
```

You’ll see: `🧑 What do you want to solve today? →`.

- Type your task and press Enter.
- Type `new` to start a fresh session.
- Type `exit` to quit.

---

### Configuration

- `config/profiles.yaml`
  - `agent`: name/id/description
  - `strategy`: planning mode and limits
    - `planning_mode`: `conservative` or `exploratory`
    - `exploration_mode`: `parallel` or `sequential` (only for `exploratory`)
    - `max_steps`, `max_lifelines_per_step`: control retries
  - `memory`: storage options; session data lands under `memory/`
  - `llm.text_generation`: choose `gemini` (default) or an Ollama model key (e.g., `phi4`, `gemma3:12b`, `qwen2.5:32b-instruct-q4_0`)
  - `mcp_servers`: list of MCP servers with `id`, `script`, `cwd`, and descriptions

- `config/models.json`
  - Select and configure the backing model for text generation and embeddings
  - For `gemini`: reads `GEMINI_API_KEY` from env
  - For `ollama` entries: the URLs point to `http://localhost:11434`

---

### How it works

1) **Perception** (`modules/perception.py`)
   - Extracts intent/entities, hints likely tools, and selects relevant MCP servers
2) **Planning** (`modules/decision.py`, `core/strategy.py`)
   - Builds an async `solve()` function using the chosen prompt template under `prompts/`
   - Modes: conservative (one tool call), exploratory parallel, exploratory sequential
3) **Execution** (`modules/action.py`)
   - Runs the generated `solve()` in a constrained sandbox and calls tools through the dispatcher
   - Limits each plan to 5 tool calls
4) **Memory** (`modules/memory.py`)
   - Persists run metadata and tool I/O per session under `memory/YYYY/MM/DD/`
5) **Tooling via MCP** (`core/session.py`)
   - Discovers tools from configured servers and routes tool calls over stdio

6) **Conversation history indexing** (`history_index/`)
   - Builds a lightweight vector index from your past sessions under `memory/`
   - Retrieves top-N similar Q/A pairs and injects them as few-shot context during planning

Build the index:

```bash
uv run -m history_index.indexer
```

Programmatic usage:

```python
from history_index.indexer import HistoryIndexer
HistoryIndexer().build()

from history_index.retriever import HistoryRetriever
retriever = HistoryRetriever()
shots = retriever.retrieve("Your new query", top_k=3)
```

---

### Available MCP servers (default)

- `math` → `mcp_server_1.py`
  - Arithmetic: `add`, `subtract`, `multiply`, `divide`, `power`, `remainder`
  - Functions: `cbrt`, `factorial`, `sin`, `cos`, `tan`, `fibonacci_numbers`
  - Transforms: `strings_to_chars_to_int`, `int_list_to_exponential_sum`
  - Images: `create_thumbnail`

- `documents` → `mcp_server_2.py`
  - RAG: `search_stored_documents` over a FAISS index built from `documents/`
  - Extraction: `convert_webpage_url_into_markdown`, `extract_pdf`
  - On first run, the server builds/updates `faiss_index/` with semantic chunking and image captioning

- `websearch` → `mcp_server_3.py`
  - Search: `duckduckgo_search_results`
  - Fetch: `download_raw_html_from_url`

You can run a server standalone for development:

```bash
python mcp_server_1.py dev
python mcp_server_2.py dev
python mcp_server_3.py dev
```

When launched by the agent, servers run over stdio automatically—no manual startup required.

---

### Working with documents (RAG)

1) Drop files into `documents/` (PDF, DOCX, MD, HTML, etc.)
2) Start the agent; the `documents` server will build or update the FAISS index under `faiss_index/`
3) Ask questions like: “Search stored documents for DLF Capbridge payment”

To force a full rebuild, delete `faiss_index/` and re-run.

---

### Example queries

- Math chain: “Find the ASCII values of INDIA and return the sum of their exponentials.”
- Web summary: “Summarize this page: https://theschoolof.ai/”
- Document Q&A: “How much was the DLF apartment payment via Capbridge?”
- Company relation: “What is the relationship between Gensol and Go-Auto?”

During a run, the agent returns either:

- `FINAL_ANSWER: ...` when done, or
- `FURTHER_PROCESSING_REQUIRED: ...` when the previous step produced content that should be summarized/used by the next step

Type `new` to start a new session; type `exit` to quit.

---

### Project structure

```text
agent.py                     # CLI entrypoint
config/                      # Agent profile, models
core/                        # Context, loop, strategy, MultiMCP session
modules/                     # Perception, planning, action, memory, modeling utils
mcp_server_1.py              # Math & utility tools
mcp_server_2.py              # RAG + webpage/PDF extraction
mcp_server_3.py              # Web search + raw content fetch
prompts/                     # Prompt templates for planning and perception
documents/                   # Your local corpus (indexed into faiss_index/)
faiss_index/                 # Auto-generated vector index + metadata
memory/                      # Persisted session traces
pyproject.toml               # Project metadata and dependencies
uv.lock                      # uv lockfile (optional)
```

---

### Tips & troubleshooting

- Missing `GEMINI_API_KEY`: set it in `.env` or environment, or switch `llm.text_generation` to an Ollama model in `config/profiles.yaml`
- RAG failing: ensure Ollama is running and the required models are pulled; delete `faiss_index/` to rebuild
- Paths on Windows: update `config/profiles.yaml` `cwd` entries to your local path
- Sandbox limits: the generated `solve()` runs with limited built-ins and a max of 5 tool calls; it can still fail if a tool contract is violated

---

### Extending

- Add tools: implement in an existing `mcp_server_*.py` with `@mcp.tool()`
- Add a new server: create `mcp_server_X.py` and register it under `config/profiles.yaml > mcp_servers`
- Modify prompts: edit files in `prompts/` to change planning/perception behavior

---