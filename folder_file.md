# Architecture du projet Book2Plate (`folder_file.md`)

### Fichiers de configuration et d'infrastructure à la racine

* **`.env.example`** : Modèle des variables d'environnement nécessaires au projet (identifiants, ports, clés API).
* **`.gitignore`** : Liste des répertoires et fichiers ignorés par Git (fichiers temporaires, environnement virtuel, gros médias).
* **`docker-compose.yml`** : Fichier de configuration Docker orchestrant la base PostgreSQL avec l'extension vectorielle pgvector.
* **`Makefile`** : Raccourcis de commandes terminal pour installer, lancer les conteneurs, formater et exécuter les tests.
* **`pyproject.toml`** : Spécification moderne du package Python, des dépendances par brique et de la configuration des outils de test.
* **`requirements.txt`** : Liste figée des dépendances Python requises pour le socle d'exécution.
* **`requirements-dev.txt`** : Liste des dépendances complémentaires dédiées aux tests, au linting et aux modules en développement.
* **`README.md`** : Guide principal présentant l'architecture globale, les fonctionnalités clés et les commandes de démarrage.

---

### Répertoire `data/` (Jeux de données et référentiels)

* **`data/`** : Répertoire parent regroupant l'ensemble des données brutes, des référentiels statiques et des jeux d'évaluation.
* **`data/raw/`** : Espace de stockage local pour vos fichiers PDF de cuisine bruts et les extractions audio temporaires.
* **`data/references/`** : Dossier regroupant les quatre bases de données ouvertes utilisées par les moteurs déterministes.
* **`data/references/flavorgraph_embeddings.pkl`** : Plongements vectoriels 300D pour calculer les substitutions moléculaires et aromatiques.
* **`data/references/open_prices.parquet`** : Base de prix réels relevés en supermarchés français issue d'Open Food Facts.
* **`data/references/ciqual_2020.csv`** : Table nutritionnelle officielle de l'ANSES contenant les teneurs en calories et macronutriments.
* **`data/references/wine_pairing_rules.json`** : Matrice structurée des règles de sommellerie et d'accords sans alcool.


* **`data/eval_datasets/`** : Jeux de recettes de référence annotés servant de référence pour les tests de non-hallucination en CI/CD.

---

### Répertoire `src/book2plate/` (Code source applicatif)

* **`src/`** : Racine des sources Python isolant le code métier des configurations annexes.
* **`src/book2plate/`** : Package principal contenant tous les sous-modules de l'application.
* **`src/book2plate/__init__.py`** : Déclare le répertoire comme package Python importable.
* **`src/book2plate/config.py`** : Charge et valide de façon typée les variables de configuration et chemins via Pydantic Settings.

#### Module `core/` (Contrats de données universels)

* **`src/book2plate/core/`** : Cœur de l'application définissant les contrats de données partagés sans dépendance externe.
* **`src/book2plate/core/__init__.py`** : Expose les modèles de données fondamentaux du module core.
* **`src/book2plate/core/enums.py`** : Énumérations strictes des unités de mesure, types de plats et contraintes alimentaires.
* **`src/book2plate/core/schemas.py`** : Schémas Pydantic v2 définissant les structures strictes d'ingrédients, étapes et recettes.

#### Module `deterministic/` (Moteurs de calculs réels — Zéro LLM)

* **`src/book2plate/deterministic/`** : Algorithmes mathématiques et déterministes fonctionnant sur les données de référence sans LLM.
* **`src/book2plate/deterministic/__init__.py`** : Expose les fonctions de calcul déterministes.
* **`src/book2plate/deterministic/chemistry.py`** : Calcule les similarités aromatiques et propose des substituts d'ingrédients via FlavorGraph.
* **`src/book2plate/deterministic/pricing.py`** : Calcule le coût réel au kilo et le budget total du panier via les données Open Prices.
* **`src/book2plate/deterministic/nutrition.py`** : Mappe les ingrédients avec la table Ciqual pour calculer les calories et macronutriments exacts.
* **`src/book2plate/deterministic/beverage_pairing.py`** : Détermine les accords vins et boissons sans alcool selon les dominantes gustatives du plat.

#### Module `ingestion/` (Extraction multimodale)

* **`src/book2plate/ingestion/`** : Pipeline d'extraction transformant des PDFs et vidéos Instagram en texte structuré.
* **`src/book2plate/ingestion/__init__.py`** : Initialise le pipeline d'ingestion.
* **`src/book2plate/ingestion/pdf_parser.py`** : Découpe les pages de livres PDF et sépare la liste d'ingrédients des instructions.
* **`src/book2plate/ingestion/insta_extractor.py`** : Récupère la légende textuelle et télécharge la piste audio des Reels Instagram via yt-dlp.
* **`src/book2plate/ingestion/audio_transcriber.py`** : Retranscrit localement la voix des vidéos culinaires en texte à l'aide de Faster-Whisper.
* **`src/book2plate/ingestion/structurer.py`** : Convertit le texte brut issu des livres ou de Whisper en un objet RecipeSchema validé.
* **`src/book2plate/ingestion/cli.py`** : Script exécutable en terminal pour tester manuellement l'ingestion d'un fichier ou d'un lien.

#### Module `storage/` (Persistance et indexation vectorielle)

* **`src/book2plate/storage/`** : Couche d'accès aux données, persistance relationnelle et recherche de similarité.
* **`src/book2plate/storage/__init__.py`** : Initialise la couche de stockage.
* **`src/book2plate/storage/database.py`** : Gère la connexion asynchrone et les sessions vers la base de données PostgreSQL.
* **`src/book2plate/storage/models.py`** : Définit les tables SQLAlchemy pour les recettes, ingrédients, clusters et retours utilisateurs.
* **`src/book2plate/storage/vector_store.py`** : Indexe les descriptions de recettes et permet la recherche par similarité avec pgvector.
* **`src/book2plate/storage/clustering.py`** : Regroupe automatiquement les variantes d'un même plat au sein de clusters vectoriels.

#### Module `engine/` (Orchestration multi-agents et fusion)

* **`src/book2plate/engine/`** : Moteur décisionnel combinant la fusion des variantes et la validation sous contrôle humain.
* **`src/book2plate/engine/__init__.py`** : Initialise le moteur d'orchestration.
* **`src/book2plate/engine/state.py`** : Définit la structure de l'état partagé circulant dans le graphe LangGraph.
* **`src/book2plate/engine/graph.py`** : Construit le graphe d'états orienté liant le filtrage, la fusion et l'approbation humaine.
* **`src/book2plate/engine/fusion_nodes.py`** : Fusionne les variantes d'un cluster en intégrant les substituts aromatiques et restes du frigo.
* **`src/book2plate/engine/guardrails.py`** : Filtre de sécurité déterministe bloquant l'inclusion d'allergènes ou d'ingrédients interdits.
* **`src/book2plate/engine/formatters.py`** : Transforme la recette validée en deux affichages (mode détaillé pas-à-pas et mode condensé aide-mémoire).

#### Module `api/` (Exposition web asynchrone)

* **`src/book2plate/api/`** : Couche d'exposition des fonctionnalités métier sous forme d'API HTTP REST.
* **`src/book2plate/api/__init__.py`** : Initialise le module d'API.
* **`src/book2plate/api/main.py`** : Point d'entrée de l'application FastAPI déclarant les middlewares et points de montage.
* **`src/book2plate/api/routes/`** : Dossier regroupant les routeurs FastAPI découpés par domaine fonctionnel.
* **`src/book2plate/api/routes/ingest.py`** : Endpoints recevant les requêtes d'ingestion de PDFs et d'URLs Instagram.
* **`src/book2plate/api/routes/recipes.py`** : Endpoints permettant de lister, consulter et filtrer les recettes et clusters enregistrés.
* **`src/book2plate/api/routes/planner.py`** : Endpoint lançant la génération de menu avec streaming asynchrone des résultats.



#### Module `ui/` (Interface utilisateur minimale)

* **`src/book2plate/ui/`** : Couche de présentation pour l'interaction utilisateur quotidienne.
* **`src/book2plate/ui/__init__.py`** : Initialise le module d'interface utilisateur.
* **`src/book2plate/ui/app.py`** : Application web Streamlit légère permettant d'importer des recettes et de visualiser les fiches condensées.

---

### Répertoire `tests/` (Suites de tests découplées)

* **`tests/`** : Répertoire parent regroupant l'ensemble des tests automatisés exécutés par pytest.
* **`tests/conftest.py`** : Déclare les fixtures partagées, mocks et objets de recettes réutilisés par tous les tests.
* **`tests/unit/`** : Tests vérifiant chaque composant de manière isolée sans réseau ni base active.
* **`tests/unit/test_schemas.py`** : Valide le respect des contraintes de typage et de validation des schémas Pydantic.
* **`tests/unit/test_pricing.py`** : Vérifie le calcul exact du coût des ingrédients à partir du fichier Open Prices.
* **`tests/unit/test_chemistry.py`** : Vérifie que le calcul de similarité cosinus FlavorGraph renvoie des substituts cohérents.
* **`tests/unit/test_guardrails.py`** : Vérifie qu'une recette contenant un allergène déclaré est systématiquement rejetée.
* **`tests/unit/test_ingestion_pdf.py`** : Teste le découpage de texte sur un exemple de page PDF sans appel externe.
* **`tests/unit/test_ingestion_insta.py`** : Teste l'extraction des légendes et le déclenchement conditionnel de la transcription.


* **`tests/integration/`** : Tests vérifiant la bonne communication entre plusieurs composants du système.
* **`tests/integration/test_clustering.py`** : Valide l'insertion de recettes dans pgvector et la création effective d'un cluster.
* **`tests/integration/test_langgraph_flow.py`** : Valide l'exécution du graphe LangGraph de bout en bout et la pause humaine.


* **`tests/evals/`** : Bancs de tests mesurant scientifiquement la qualité des modèles.
* **`tests/evals/test_faithfulness.py`** : Évalue via Ragas ou DeepEval que la recette fusionnée n'invente aucun ingrédient ni étape.