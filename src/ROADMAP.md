# Plan d'action technique — Projet `Book2Plate`

## 1. Synthèse du projet et état des lieux

* **Objectif :** Moteur modulaire d'ingestion multimodale (PDFs, Instagram), clustering de variantes de recettes réelles (zéro invention) et enrichissement déterministe (chimie des saveurs, prix réels, nutrition) avec génération Dual-View (vue pas-à-pas vs fiche condensée).
* **Environnement validé :** Windows / PowerShell, Python 3.11+, environnement virtuel `.venv`, `pyproject.toml` avec `testpaths = ["src/tests"]`.
* **Données de référence locales (`data/references/`) :**
* `flavorgraph_embeddings.pkl` : Plongements vectoriels 300D (~8 298 nœuds).


* `nodes_191120.csv` : Table de mapping (`node_id`, `name`, `node_type`).


* `open_prices.parquet` : Base de prix réels relevés en supermarché (~31 Mo).
* `ciqual_2020.csv` : Table nutritionnelle officielle de l'ANSES (~3,5 Mo).
* `wine_pairing_rules.json` : Référentiel d'accords mets-vins et alternatives sans alcool.


* **État d'avancement :**
* **Étape 0 (Core & Schemas) :** Terminée. Les schémas Pydantic v2 (`RecipeSchema`, `IngredientItem`, `CookingStep`, énumérations) sont en place et validés.
* **Étape 1 (Moteurs déterministes) :** En cours. `chemistry.py` charge correctement les vecteurs 300D et le mapping de nœuds. Constat scientifique validé : FlavorGraph mesure les **accords gustatifs / co-occurrences (*Food Pairing*)** et non les substitutions strictes.





---

## 2. Feuille de route détaillée par phases

### Phase 1 : Finalisation du socle déterministe (`src/book2plate/deterministic/`)

*Principe directeur : 100 % algorithmique, zéro appel API externe, temps d'exécution < 50 ms par appel.*

* **Tâche 1.1 — Consolidation de `chemistry.py` (Flavor Pairing & Substitutions) :**
* Renommer la méthode actuelle en `find_flavor_pairings(ingredient_name: str, top_k=5)` pour identifier les ingrédients qui s'associent naturellement avec l'aliment cible.


* Ajouter une méthode `find_substitutes(ingredient_name: str, top_k=3)` combinant similarité cosinus et filtrage par catégorie (recherche de substituts uniquement au sein du même groupe alimentaire pour éviter de remplacer de l'ail par de la sauce ou de la viande).

* **Piste d'amélioration :** étudier différentes formules de métrique et méthodes d'agrégation des relations entre plusieurs ingrédients, afin d'adapter les pairages aux combinaisons et à la nature des éléments.


* *Validation :* `pytest src/tests/unit/test_chemistry.py` au vert.


* **Tâche 1.2 — Moteur d'estimation budgétaire réelle (`pricing.py`) :**
* Exploiter `open_prices.parquet` via **DuckDB** en mémoire pour requêter instantanément sans charger l'intégralité du fichier en RAM.
* Implémenter `estimate_ingredient_cost(ingredient_name: str, quantity_g: float) -> int` : normaliser le nom, calculer le prix médian au kilo en supermarché français et renvoyer le coût calculé en centimes d'euro.
* *Validation :* `src/tests/unit/test_pricing.py` vérifiant qu'un échantillon (ex. 250 g de beurre ou 500 g de pâtes) retourne un montant réaliste non nul.


* **Tâche 1.3 — Moteur nutritionnel déterministe (`nutrition.py`) :**
* Parser `ciqual_2020.csv` pour faire correspondre un ingrédient avec ses valeurs officielles pour 100 g (calories kcal, protéines, lipides, glucides, fibres).
* Implémenter `calculate_recipe_nutrition(ingredients: list[IngredientItem]) -> NutritionInfo`.
* *Validation :* `src/tests/unit/test_nutrition.py` calculant les macronutriments exacts d'un assemblage test.


* **Tâche 1.4 — Moteur d'accords mets-boissons (`beverage_pairing.py`) :**
* Parser `wine_pairing_rules.json` pour matcher les dominantes du plat (gras, acidité, épices, protéines dominantes).
* Implémenter `get_beverage_pairing(recipe: RecipeSchema) -> tuple[str, str]` : renvoyer une recommandation de vin (cépage / région) et une alternative sans alcool basée sur l'équilibre gustatif.
* *Validation :* `src/tests/unit/test_beverage_pairing.py` au vert.



---

### Phase 2 : Pipeline d'ingestion multimodale (`src/book2plate/ingestion/`)

*Principe directeur : Convertir n'importe quel document non structuré en objet `RecipeSchema` strictement typé.*

* **Tâche 2.1 — Parseur de livres PDF (`pdf_parser.py`) :**
* Utiliser `pdfplumber` pour extraire le texte brut par page tout en préservant la distinction visuelle entre colonnes d'ingrédients et paragraphes d'instructions.
* Implémenter une méthode `extract_recipe_from_pdf(pdf_path: Path, page_num: int) -> str`.


* **Tâche 2.2 — Extracteur Instagram avec fallback audio (`insta_extractor.py` & `audio_transcriber.py`) :**
* Utiliser `yt-dlp` pour récupérer les métadonnées et la légende textuelle du post Instagram / Reel.
* *Branchement conditionnel :* Si la légende contient les ingrédients et étapes, arrêter l'extraction. Si la légende est vide ou tronquée, extraire la piste audio (`.mp3`) et la transcrire localement via `faster-whisper` (modèle `base` ou `small`).


* **Tâche 2.3 — Normalisation et structuration LLM (`structurer.py`) :**
* Envoyer le texte brut extrait (du PDF ou de Whisper) vers un LLM configuré avec une sortie contrainte (*structured output* / JSON mode) mappée sur `RecipeSchema`.
* Valider automatiquement la conformité avec Pydantic v2.


* **Tâche 2.4 — CLI de test autonome (`cli.py`) :**
* Permettre de tester l'ingestion directement en ligne de commande :
`python -m book2plate.ingestion.cli --pdf path/to/page.pdf`
`python -m book2plate.ingestion.cli --url "[https://instagram.com/reel/](https://instagram.com/reel/)..."`
* *Validation :* `src/tests/unit/test_ingestion_pdf.py` et `test_ingestion_insta.py` avec des mocks audio/réseau.



---

### Phase 3 : Stockage relationnel et clustering vectoriel (`src/book2plate/storage/`)

*Principe directeur : Identifier les variantes réelles d'un même plat à travers plusieurs sources sans inventer de recettes.*

* **Tâche 3.1 — Schéma relationnel et persistance (`models.py` & `database.py`) :**
* Démarrer PostgreSQL avec `pgvector` via `docker compose up -d`.
* Définir les modèles SQLAlchemy : table `recipes`, table `recipe_ingredients`, table `clusters`.


* **Tâche 3.2 — Indexation vectorielle (`vector_store.py`) :**
* Générer un embedding sur la signature de la recette (titre + liste d'ingrédients).
* Créer un index vectoriel `HNSW` ou `IVFFlat` avec `pgvector` pour permettre des recherches par similarité cosinus.


* **Tâche 3.3 — Algorithme de clustering de variantes (`clustering.py`) :**
* Comparer une recette nouvellement insérée aux recettes existantes.
* Si la similarité vectorielle dépasse un seuil (ex. 0.85), regrouper automatiquement la recette dans le même cluster fonctionnel (ex. cluster *"Risotto aux champignons"*).
* *Validation :* `src/tests/integration/test_clustering.py` vérifiant que deux recettes proches issues de deux sources distinctes sont associées au même identifiant de cluster.



---

### Phase 4 : Moteur agentique et fusion intelligente (`src/book2plate/engine/`)

*Principe directeur : Fusionner les meilleures techniques d'un cluster en respectant les contraintes utilisateur sous supervision humaine.*

* **Tâche 4.1 — Modélisation de l'état LangGraph (`state.py`) :**
* Définir `PlanState` (recettes du cluster sélectionné, ingrédients du frigo à écouler, allergènes interdits, recette fusionnée intermédiaire, statut d'approbation humaine).


* **Tâche 4.2 — Nœuds de traitement (`fusion_nodes.py`, `guardrails.py`) :**
* *Nœud Fusion :* Réconcilie les étapes des recettes sources en comblant les manques éventuels via les fonctions déterministes validées en Phase 1.
* *Nœud Garde-fous (*Guardrails*) :* Contrôle déterministe strict rejetant toute recette contenant un allergène déclaré par l'utilisateur.


* **Tâche 4.3 — Génération Dual-View (`formatters.py`) :**
* *Vue Détaillée :* Déroulé complet pas-à-pas avec minutage.
* *Vue Condensée ("Cheatsheet") :* 4 puces critiques (quantités regroupées, températures de saisie/cuisson, durées clés) pour cuisinier aguerri.


* **Tâche 4.4 — Point de contrôle humain (*Human-in-the-Loop*) :**
* Configurer une interruption d'état LangGraph (`interrupt_before`) attendant l'approbation de l'utilisateur (`valider / ajuster`) avant de finaliser la recette.
* *Validation :* `src/tests/integration/test_langgraph_flow.py`.



---

### Phase 5 : Observabilité, Banc d'évaluation et Interface (`api/`, `ui/`, `evals/`)

*Principe directeur : Traçabilité des coûts de production, preuve de non-hallucination et interface épurée.*

* **Tâche 5.1 — Observabilité avec Langfuse :**
* Instrumenter les nœuds du graphe pour enregistrer la latence d'exécution, la consommation de tokens et le coût financier par requête.


* **Tâche 5.2 — Banc d'évaluation de non-hallucination (`tests/evals/test_faithfulness.py`) :**
* Construire un jeu de 15 cas de test (*golden dataset* dans `data/eval_datasets/`).
* Utiliser un framework d'évaluation (Ragas ou DeepEval) pour vérifier que le score de fidélité contextuelle (*Faithfulness*) dépasse 0.90 (les étapes et ingrédients de la fusion proviennent exclusivement des livres sources).


* **Tâche 5.3 — Backend FastAPI (`src/book2plate/api/`) :**
* Routeurs `/api/ingest`, `/api/recipes`, `/api/plan`.


* **Tâche 5.4 — Interface Streamlit (`src/book2plate/ui/app.py`) :**
* Volet Ingestion : Déposer un PDF ou coller une URL Instagram.
* Volet Cuisine : Sélectionner des ingrédients restants -> Afficher la recette fusionnée avec toggle Vue Détaillée / Vue Condensée et affichage du coût réel au centime près.



---

## 3. Matrice de dépendances entre les briques

| Brique | Fichiers sources | Dépendances externes | Dépendances internes |
| --- | --- | --- | --- |
| **Chimie (`chemistry`)** | `flavorgraph_embeddings.pkl`, `nodes_191120.csv`<br> | NumPy | `core.schemas` |
| **Budget (`pricing`)** | `open_prices.parquet` | DuckDB / PyArrow | `core.schemas` |
| **Nutrition (`nutrition`)** | `ciqual_2020.csv` | Pandas | `core.schemas` |
| **Accords (`beverage_pairing`)** | `wine_pairing_rules.json` | Aucune (JSON natif) | `core.schemas` |
| **Ingestion PDF** | Fichiers PDF bruts | `pdfplumber` | `core.schemas` |
| **Ingestion Instagram** | URLs publiques | `yt-dlp`, `faster-whisper` | `core.schemas` |
| **Stockage & Clustering** | PostgreSQL + pgvector | SQLAlchemy, psycopg | `core.schemas` |
| **Orchestration Agent** | Graphe LangGraph | LangGraph, Langfuse | Toutes les briques ci-dessus |

---

## 4. Prompt de reprise de contexte (Pour les sessions futures)

Pour reprendre le travail ultérieurement sans avoir à réexpliquer le projet, copiez-collez ce paragraphe :

> « Nous développons le projet **Book2Plate** (Python 3.11 sous Windows/PowerShell). Le plan d'action complet est consigné dans `ROADMAP.md`.
> L'Étape 0 (`core/schemas.py`) est terminée et testée.
> Dans l'Étape 1 (`deterministic/`), `chemistry.py` est fonctionnel avec `flavorgraph_embeddings.pkl` et `nodes_191120.csv` (Flavor Pairing validé).
> Nous reprenons à la **Tâche 1.2 : Implémentation du moteur d'estimation budgétaire `pricing.py` avec DuckDB sur `open_prices.parquet**`, accompagné de son test unitaire `src/tests/unit/test_pricing.py`. Voici le code actuel et nous avançons pas à pas selon le plan. »
> 
>