# Book2Plate Project Architecture (`folder_file.md`)

### Configuration and Infrastructure Files at the Root

* **`.env.example`**: Template for the environment variables required by the project (credentials, ports, API keys).
* **`.gitignore`**: List of directories and files ignored by Git (temporary files, virtual environment, large media).
* **`docker-compose.yml`**: Docker configuration file orchestrating the PostgreSQL database with the pgvector extension.
* **`Makefile`**: Terminal command shortcuts for installing, starting containers, formatting, and running tests.
* **`pyproject.toml`**: Modern Python package specification, per-component dependencies, and tool configuration.
* **`requirements.txt`**: Pinned list of Python dependencies required for the runtime base.
* **`requirements-dev.txt`**: Additional dependencies for testing, linting, and modules under development.
* **`README.md`**: Main guide presenting the overall architecture, key features, and startup commands.

---

### `data/` Directory (Datasets and Reference Data)

* **`data/`**: Parent directory grouping all raw data, static reference datasets, and evaluation sets.
* **`data/raw/`**: Local storage space for raw cooking PDF files and temporary audio extractions.
* **`data/references/`**: Folder containing the four open databases used by the deterministic engines.
  * **`data/references/flavorgraph_embeddings.pkl`**: 300D vector embeddings for computing molecular and aromatic substitutions.
  * **`data/references/open_prices.parquet`**: Real prices collected in French supermarkets from Open Food Facts.
  * **`data/references/ciqual_2020.csv`**: Official ANSES nutritional table containing calorie and macronutrient content.
  * **`data/references/wine_pairing_rules.json`**: Structured matrix of sommelier rules and non-alcoholic pairing alternatives.
* **`data/eval_datasets/`**: Annotated reference recipe sets used as ground truth for non-hallucination tests in CI/CD.

---

### `src/book2plate/` Directory (Application Source Code)

* **`src/`**: Python source root isolating business logic from ancillary configurations.
* **`src/book2plate/`**: Main package containing all application sub-modules.
* **`src/book2plate/__init__.py`**: Declares the directory as an importable Python package.
* **`src/book2plate/config.py`**: Loads and type-validates configuration variables and paths via Pydantic Settings.

#### `core/` Module (Universal Data Contracts)

* **`src/book2plate/core/`**: Application core defining shared data contracts with no external dependencies.
* **`src/book2plate/core/__init__.py`**: Exposes the fundamental data models from the core module.
* **`src/book2plate/core/enums.py`**: Strict enumerations for units of measure, dish types, and dietary constraints.
* **`src/book2plate/core/schemas.py`**: Pydantic v2 schemas defining the strict structures for ingredients, steps, and recipes.

#### `deterministic/` Module (Real Computation Engines — Zero LLM)

* **`src/book2plate/deterministic/`**: Mathematical and deterministic algorithms operating on reference data without any LLM.
* **`src/book2plate/deterministic/__init__.py`**: Exposes the deterministic computation functions.
* **`src/book2plate/deterministic/chemistry.py`**: Computes aromatic similarities and suggests ingredient substitutes via FlavorGraph.
* **`src/book2plate/deterministic/pricing.py`**: Calculates the real cost per kilogram and the total basket budget using Open Prices data.
* **`src/book2plate/deterministic/nutrition.py`**: Maps ingredients to the Ciqual table to compute exact calories and macronutrients.
* **`src/book2plate/deterministic/beverage_pairing.py`**: Determines wine and non-alcoholic beverage pairings based on the dish's dominant flavor profile.

#### `ingestion/` Module (Multimodal Extraction)

* **`src/book2plate/ingestion/`**: Extraction pipeline transforming PDFs and Instagram videos into structured text.
* **`src/book2plate/ingestion/__init__.py`**: Initializes the ingestion pipeline.
* **`src/book2plate/ingestion/pdf_parser.py`**: Splits PDF book pages and separates the ingredient list from the instructions.
* **`src/book2plate/ingestion/insta_extractor.py`**: Retrieves the text caption and downloads the audio track from Instagram Reels via yt-dlp.
* **`src/book2plate/ingestion/audio_transcriber.py`**: Locally transcribes the voice from culinary videos to text using Faster-Whisper.
* **`src/book2plate/ingestion/structurer.py`**: Converts raw text from books or Whisper into a validated `RecipeSchema` object.
* **`src/book2plate/ingestion/cli.py`**: Terminal-executable script for manually testing the ingestion of a file or link.

#### `storage/` Module (Persistence and Vector Indexing)

* **`src/book2plate/storage/`**: Data access layer, relational persistence, and similarity search.
* **`src/book2plate/storage/__init__.py`**: Initializes the storage layer.
* **`src/book2plate/storage/database.py`**: Manages the asynchronous connection and sessions to the PostgreSQL database.
* **`src/book2plate/storage/models.py`**: Defines the SQLAlchemy tables for recipes, ingredients, clusters, and user feedback.
* **`src/book2plate/storage/vector_store.py`**: Indexes recipe descriptions and enables similarity search with pgvector.
* **`src/book2plate/storage/clustering.py`**: Automatically groups variants of the same dish into vector clusters.

#### `engine/` Module (Multi-Agent Orchestration and Merging)

* **`src/book2plate/engine/`**: Decision engine combining variant merging and human-supervised validation.
* **`src/book2plate/engine/__init__.py`**: Initializes the orchestration engine.
* **`src/book2plate/engine/state.py`**: Defines the structure of the shared state flowing through the LangGraph graph.
* **`src/book2plate/engine/graph.py`**: Builds the directed state graph linking filtering, merging, and human approval.
* **`src/book2plate/engine/fusion_nodes.py`**: Merges cluster variants by integrating aromatic substitutes and fridge leftovers.
* **`src/book2plate/engine/guardrails.py`**: Deterministic safety filter blocking the inclusion of allergens or banned ingredients.
* **`src/book2plate/engine/formatters.py`**: Transforms the validated recipe into two output formats (detailed step-by-step mode and condensed cheat-sheet mode).

#### `api/` Module (Asynchronous Web Exposure)

* **`src/book2plate/api/`**: Layer exposing business features as an HTTP REST API.
* **`src/book2plate/api/__init__.py`**: Initializes the API module.
* **`src/book2plate/api/main.py`**: FastAPI application entry point declaring middlewares and mount points.
* **`src/book2plate/api/routes/`**: Folder containing FastAPI routers split by functional domain.
* **`src/book2plate/api/routes/ingest.py`**: Endpoints receiving ingestion requests for PDFs and Instagram URLs.
* **`src/book2plate/api/routes/recipes.py`**: Endpoints for listing, viewing, and filtering saved recipes and clusters.
* **`src/book2plate/api/routes/planner.py`**: Endpoint launching menu generation with asynchronous result streaming.

#### `ui/` Module (Minimal User Interface)

* **`src/book2plate/ui/`**: Presentation layer for day-to-day user interaction.
* **`src/book2plate/ui/__init__.py`**: Initializes the user interface module.
* **`src/book2plate/ui/app.py`**: Lightweight Streamlit web application for importing recipes and viewing condensed cards.

---

### `tests/` Directory (Decoupled Test Suites)

* **`tests/`**: Parent directory grouping all automated tests run by pytest.
* **`tests/conftest.py`**: Declares shared fixtures, mocks, and recipe objects reused across all tests.
* **`tests/unit/`**: Tests verifying each component in isolation, with no network or active database.
  * **`tests/unit/test_schemas.py`**: Validates that Pydantic schema typing and validation constraints are respected.
  * **`tests/unit/test_pricing.py`**: Verifies the exact ingredient cost calculation from the Open Prices file.
  * **`tests/unit/test_chemistry.py`**: Verifies that the FlavorGraph cosine similarity computation returns consistent substitutes.
  * **`tests/unit/test_guardrails.py`**: Verifies that a recipe containing a declared allergen is systematically rejected.
  * **`tests/unit/test_ingestion_pdf.py`**: Tests text splitting on a sample PDF page without external calls.
  * **`tests/unit/test_ingestion_insta.py`**: Tests caption extraction and conditional triggering of transcription.
* **`tests/integration/`**: Tests verifying correct communication between multiple system components.
  * **`tests/integration/test_clustering.py`**: Validates recipe insertion into pgvector and effective cluster creation.
  * **`tests/integration/test_langgraph_flow.py`**: Validates end-to-end LangGraph graph execution and the human pause.
* **`tests/evals/`**: Test benches scientifically measuring model quality.
  * **`tests/evals/test_faithfulness.py`**: Evaluates via Ragas or DeepEval that the merged recipe invents no ingredient or step.