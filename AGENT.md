# `agent.md` — Directives d'ingénierie pour Book2Plate

## 1. Contexte et mission du projet

**Book2Plate** est un moteur d'ingénierie logicielle permettant de découper, regrouper (*clustering*), enrichir et fusionner des recettes issues de livres de cuisine (PDF) et de réseaux sociaux (Instagram/Reels) pour générer des plannings de repas réalistes et des fiches condensées pour cuisiniers aguerris.

Le projet applique une séparation stricte entre :

* **Les moteurs déterministes :** calculs de prix réels, substitutions chimiques basées sur la science aromatique, tables nutritionnelles officielles et règles de sommellerie.
* **Les modèles probabilistes / LLMs :** normalisation textuelle multimodale et assistance à la fusion créative, toujours encadrés par des schémas stricts et des garde-fous.

---

## 2. Règles fondamentales et principes non-négociables

### A. Typage strict et validation Pydantic v2

* Tout échange de données entre modules doit s'appuyer exclusivement sur les contrats définis dans `book2plate.core.schemas`.
* Aucun dictionnaire Python brut (`dict[str, Any]`) non typé ne doit circuler entre les couches logicielles.
* Les validations doivent être défensives : quantités strictement positives, unités issues de `UnitEnum`, durées supérieures ou égales à zéro.

### B. Moteurs déterministes sans dépendance LLM

* Le module `book2plate.deterministic` ne doit effectuer **aucun appel d'API LLM**, direct ou indirect.
* Les prix doivent provenir uniquement de calculs sur `open_prices.parquet` via DuckDB ou Polars.
* Les substitutions d'ingrédients doivent découler du calcul de similarité cosinus sur les vecteurs de `flavorgraph_embeddings.pkl`.
* Les macronutriments doivent provenir du référentiel `ciqual_2020.csv`.

### C. Découplage strict des modules (Architecture modulaire)

* Chaque sous-dossier de `src/book2plate/` doit pouvoir s'exécuter et être testé de manière totalement isolée.
* Aucun test unitaire dans `tests/unit/` ne doit nécessiter :
* Une connexion réseau internet active.
* Une base de données PostgreSQL en fonctionnement (utiliser des mocks ou des structures en mémoire).
* Un appel API externe payant.

### D. Gestion de l'asynchronisme

* Les endpoints d'API (`FastAPI`) et les flux de streaming d'agents doivent privilégier la programmation asynchrone (`async` / `await`).
* L'I/O bloquante (lecture disque lourde de modèles ou parsing audio volumineux) doit être déléguée à des exécuteurs de threads (`asyncio.to_thread`) pour ne jamais bloquer la boucle d'événements.

---

## 3. Dépendances de données de référence

Les 4 fichiers suivants sont stockés en local dans `data/references/` et ne doivent jamais être commités sur Git :

1. `flavorgraph_embeddings.pkl` : Dictionnaire d'embeddings 300D pour les calculs aromatiques.
2. `open_prices.parquet` : Base de prix réels relevés en supermarché.
3. `ciqual_2020.csv` : Table nutritionnelle officielle de l'ANSES.
4. `wine_pairing_rules.json` : Règles déterministes d'accords mets-boissons.

L'accès à ces chemins doit toujours s'effectuer via l'objet centralisé `book2plate.config.settings`.

---

## 4. Normes de code et conventions de développement

### Style et qualité

* Respect de PEP 8 avec une longueur maximale de ligne fixée à 120 caractères.
* Formatage et linting gérés exclusivement par **Ruff** (`ruff check` et `ruff format`).
* Fonctions systématiquement annotées avec des *type hints* Python stricts.
* Documentation courte sous forme de docstring pour chaque fonction publique expliquant les entrées, sorties et effets de bord éventuels.

### Structure des tests

* `tests/unit/` : Tests unitaires instantanés validant la logique interne d'une seule fonction/classe.
* `tests/integration/` : Tests validant la persistance en base (PostgreSQL / `pgvector`) et les pipelines LangGraph.
* `tests/evals/` : Bancs de tests mesurant les métriques de non-hallucination (*faithfulness*, *context precision*) via Ragas ou DeepEval.

---

## 5. Commandes de référence

| Objectif | Commande terminal |
| --- | --- |
| Exécuter les tests unitaires | `pytest tests/unit/ -v` |
| Exécuter un test spécifique | `pytest tests/unit/test_schemas.py -v` |
| Vérifier le formatage et le linting | `ruff check src tests` |
| Appliquer les corrections automatiques de code | `ruff format src tests` |
| Lancer l'infrastructure locale (DB) | `docker compose up postgres -d` |
| Arrêter l'infrastructure locale | `docker compose down` |

---

## 6. Protocole d'intervention pour l'agent

Lorsqu'une tâche de code est confiée à l'agent :

1. **Vérifier les contrats :** Consulter d'abord `src/book2plate/core/schemas.py` pour s'assurer que les modèles de données existants sont respectés.
2. **Implémenter la logique :** Rédiger le code dans le module cible en limitant l'importation de dépendances inutiles.
3. **Créer ou mettre à jour le test associé :** Toute nouvelle fonction doit être accompagnée de son cas de test unitaire dans `tests/unit/`.
4. **Vérifier l'absence de régression :** Lancer `pytest` et `ruff check` avant de considérer la tâche comme terminée.