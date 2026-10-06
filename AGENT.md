# `agent.md` — Engineering Directives for Book2Plate

## 1. Project Context and Mission

**Book2Plate** is a software engineering engine that extracts, clusters, enriches, and merges recipes from cookbooks (PDF) and social media (Instagram/Reels) to generate realistic meal plans and condensed recipe cards for experienced cooks.

The project enforces a strict separation between:

* **Deterministic engines:** real price calculations, chemistry-based substitutions grounded in flavor science, official nutritional tables, and sommelier pairing rules.
* **Probabilistic models / LLMs:** multimodal text normalization and creative merge assistance, always constrained by strict schemas and guardrails.

---

## 2. Fundamental Rules and Non-Negotiable Principles

### A. Strict Typing and Pydantic v2 Validation

* All data exchanged between modules must rely exclusively on contracts defined in `book2plate.core.schemas`.
* No untyped raw Python dictionaries (`dict[str, Any]`) may flow between software layers.
* Validations must be defensive: strictly positive quantities, units from `UnitEnum`, durations greater than or equal to zero.

### B. Deterministic Engines with No LLM Dependency

* The `book2plate.deterministic` module must make **no LLM API calls**, direct or indirect.
* Prices must come solely from calculations on `open_prices.parquet` via DuckDB or Polars.
* Ingredient substitutions must result from cosine similarity calculations on the `flavorgraph_embeddings.pkl` vectors.
* Macronutrients must come from the `ciqual_2020.csv` reference dataset.

### C. Strict Module Decoupling (Modular Architecture)

* Each subdirectory of `src/book2plate/` must be executable and testable in complete isolation.
* No unit test in `tests/unit/` may require:
  * An active internet connection.
  * A running PostgreSQL database (use mocks or in-memory structures).
  * A paid external API call.

### D. Async Management

* API endpoints (`FastAPI`) and agent streaming pipelines should favor async programming (`async` / `await`).
* Blocking I/O (heavy model reads or large audio parsing) must be delegated to thread executors (`asyncio.to_thread`) to never block the event loop.

---

## 3. Reference Data Dependencies

The following 4 files are stored locally in `data/references/` and must never be committed to Git:

1. `flavorgraph_embeddings.pkl`: Dictionary of 300D embeddings for aromatic calculations.
2. `open_prices.parquet`: Real prices collected in supermarkets.
3. `ciqual_2020.csv`: Official nutritional table from ANSES.
4. `wine_pairing_rules.json`: Deterministic food-and-beverage pairing rules.

Access to these paths must always go through the centralized `book2plate.config.settings` object.

---

## 4. Code Standards and Development Conventions

### Style and Quality

* Comply with PEP 8 with a maximum line length of 120 characters.
* Formatting and linting managed exclusively by **Ruff** (`ruff check` and `ruff format`).
* All functions must be annotated with strict Python type hints.
* Short docstring documentation for every public function explaining inputs, outputs, and any side effects.

### Test Structure

* `tests/unit/`: Instant unit tests validating the internal logic of a single function/class.
* `tests/integration/`: Tests validating database persistence (PostgreSQL / `pgvector`) and LangGraph pipelines.
* `tests/evals/`: Test benches measuring non-hallucination metrics (*faithfulness*, *context precision*) via Ragas or DeepEval.

---

## 5. Reference Commands

| Goal | Terminal Command |
| --- | --- |
| Run unit tests | `pytest tests/unit/ -v` |
| Run a specific test | `pytest tests/unit/test_schemas.py -v` |
| Check formatting and linting | `ruff check src tests` |
| Apply automatic code fixes | `ruff format src tests` |
| Start local infrastructure (DB) | `docker compose up postgres -d` |
| Stop local infrastructure | `docker compose down` |

---

## 6. Agent Intervention Protocol

When a coding task is assigned to the agent:

1. **Check contracts:** First consult `src/book2plate/core/schemas.py` to ensure existing data models are respected.
2. **Implement the logic:** Write the code in the target module, limiting unnecessary dependency imports.
3. **Create or update the associated test:** Every new function must be accompanied by its unit test case in `tests/unit/`.
4. **Verify no regression:** Run `pytest` and `ruff check` before considering the task complete.