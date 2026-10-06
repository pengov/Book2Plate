# Book2Plate

> From cookbook to optimized meal plan: a modular multimodal ingestion engine for clustering recipe variants and deterministic enrichment (flavor chemistry, real prices & nutrition).

---

## 1. Overview

* **Structured multimodal ingestion:** deterministic extraction and normalization of recipes from static cookbooks (PDF) and social media posts (Instagram Reels via text extraction and local speech-to-text with Faster-Whisper).
* **Variant clustering:** vectorial grouping of equivalent recipes across multiple books to identify real variants already validated by chefs.
* **Deterministic calculations:**
    * **Real prices:** budget estimation backed by the open collaborative **Open Prices** database (Open Food Facts).
    * **Flavor chemistry:** scientifically grounded aromatic substitutions via cosine similarity on **FlavorGraph** 300D embeddings.
    * **Nutrition:** macronutrient calculation from the official **Ciqual** table (ANSES).
    * **Sommelier pairings:** deterministic food-and-beverage pairing matrix with non-alcoholic alternatives.


* **Dual-View Generation:** on-demand double output:
    * *Detailed Mode:* step-by-step guidance for beginners.
    * *Condensed Mode:* quick-reference card for experienced cooks.


* **Human-in-the-Loop agentic architecture:** state-graph orchestration (**LangGraph**) with guardrails and mandatory breakpoints before meal plan confirmation.

---

## 2. Architecture Principles

The project adopts a layered separation of concerns:

* **`core` layer:** universal data contracts governed by strict Pydantic v2 schemas (`RecipeSchema`, `IngredientItem`, `CookingStep`).
* **`deterministic` layer:** pure functions and local tabular queries (DuckDB / Polars / Scikit-Learn) with no network calls or LLM APIs.
* **`ingestion` layer:** extraction pipeline with PDF chunking (`pdfplumber`) and conditional fallback to local Whisper (`faster-whisper`) for audio.
* **`storage` layer:** relational persistence and vector indexing (`pgvector` under PostgreSQL) for semantic querying and clustering.
* **`engine` layer:** LangGraph finite state machine governing the merge flow, safety rules, and user interruptions.
* **`api` & `ui` layers:** asynchronous FastAPI backend and a clean Streamlit control interface.

---

## 3. Required Reference Data

The `data/references/` folder contains the open reference datasets required to run the deterministic engines locally:

| File | Source | Technical Role |
| --- | --- | --- |
| `flavorgraph_embeddings.pkl` | GitHub `lamypark/FlavorGraph` | 300D embeddings for aromatic similarity and molecular substitution |
| `open_prices.parquet` | data.gouv.fr / Open Food Facts | Real prices collected in French supermarkets for accurate basket costing |
| `ciqual_2020.csv` | ANSES / data.gouv.fr | Official nutritional composition table (calories, proteins, carbohydrates, fats) |
| `wine_pairing_rules.json` | Open-source reference | Food-and-beverage pairing rules based on flavor profiles and fat/acidity content |

*Note: these files are ignored by Git and must be placed manually in the `data/references/` directory.*

---

## 4. Prerequisites and Installation

### System Requirements

* Python > 3.11
* Docker and Docker Compose
* FFmpeg (required for audio extraction by `yt-dlp` and `faster-whisper`)

### Step-by-Step Installation

1. **Clone the repository:**
```bash
git clone https://github.com/your-account/book2plate.git
cd book2plate

```


2. **Create and activate the virtual environment:**
```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

```


3. **Install dependencies:**
```bash
pip install --upgrade pip
pip install -e ".[dev,ingest,engine,api]"

```


4. **Configure environment variables:**
```bash
cp .env.example .env
# Fill in the variables in .env as needed

```


5. **Start the infrastructure containers:**
```bash
make up

```


*This command starts PostgreSQL with the `pgvector` extension on port 5432.*

---

## 5. Useful Commands (Makefile)

The project includes a `Makefile` to standardize workflows:

* `make help`: Displays all available commands.
* `make install`: Installs the project in editable mode with development dependencies.
* `make up`: Starts the PostgreSQL database (`pgvector`) in the background.
* `make down`: Stops and cleans up Docker containers.
* `make test`: Runs the full unit test suite via pytest.
* `make lint`: Checks code quality and typing via Ruff.
* `make format`: Automatically applies style and formatting fixes.

---

## 6. Project Structure

A detailed view of the responsibility of each folder and file is available in the [`folder_file.md`](./folder_file.md) document.

---

## 7. Software Quality and Evaluation Metrics

* **Unit tests:** no test in `tests/unit/` requires a network connection or access to a paid third-party service.
* **Non-hallucination evaluation:** the project includes contextual faithfulness tests in `tests/evals/` ensuring that recipe merges strictly respect the ingredients and steps from the source books.
* **Full observability:** traceability of inference times, processing latency, and token consumption via Langfuse.

---

## 8. License

This project is distributed under the **TO BE DEFINED** license. See the `LICENSE` file for details.