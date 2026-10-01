import csv
import pickle
from pathlib import Path

import numpy as np
import pytest

from book2plate.config import settings
from book2plate.deterministic.chemistry import FlavorChemistryEngine


@pytest.fixture(scope="module")
def engine() -> FlavorChemistryEngine:
    """Charge FlavorGraph pour les tests qui vérifient les données de référence."""
    if not settings.flavorgraph_path.exists() or not settings.flavorgraph_nodes_path.exists():
        pytest.skip("Fichiers FlavorGraph absents de data/references/")
    return FlavorChemistryEngine()


@pytest.fixture
def synthetic_engine() -> FlavorChemistryEngine:
    """Construit un moteur en mémoire avec quatre embeddings unitaires déterministes."""
    instance = object.__new__(FlavorChemistryEngine)
    instance._embeddings = {
        "garlic": np.array([1.0, 0.0], dtype=np.float32),
        "basil": np.array([0.0, 1.0], dtype=np.float32),
        "onion": np.array([0.8, 0.6], dtype=np.float32),
        "lemon": np.array([-1.0, 0.0], dtype=np.float32),
        "opposite": np.array([-1.0, 0.0], dtype=np.float32),
    }
    instance._norms = {name: 1.0 for name in instance._embeddings}
    return instance


def test_loads_enough_ingredients(engine: FlavorChemistryEngine) -> None:
    """Vérifie que le jeu FlavorGraph de référence contient suffisamment d'ingrédients."""
    assert engine.total_ingredients > 500


def test_ingredient_names_are_text(engine: FlavorChemistryEngine) -> None:
    """Vérifie que les noms chargés sont des chaînes textuelles non vides."""
    for name in engine.ingredient_names()[:50]:
        assert isinstance(name, str) and name and not name.isdigit()


def test_known_ingredients_present(engine: FlavorChemistryEngine) -> None:
    """Vérifie la présence de quelques ingrédients attendus dans FlavorGraph."""
    known = {"garlic oil", "leek", "zucchini", "onion"}
    missing = known - set(engine.ingredient_names())
    assert not missing, f"Ingrédients absents : {missing}"


def test_find_flavor_pairings_returns_list(engine: FlavorChemistryEngine) -> None:
    """Vérifie que la recherche simple retourne une liste."""
    assert isinstance(engine.find_flavor_pairings("garlic_oil", top_k=3), list)


def test_find_flavor_pairings_format(engine: FlavorChemistryEngine) -> None:
    """Vérifie le format et le domaine des scores de pairage."""
    results = engine.find_flavor_pairings("garlic_oil", top_k=3, min_similarity=0.0)
    assert len(results) > 0
    name, score = results[0]
    assert isinstance(name, str) and not name.isdigit()
    assert 0.0 <= score <= 1.0


def test_find_flavor_pairings_top_k(engine: FlavorChemistryEngine) -> None:
    """Vérifie que la recherche simple ne dépasse pas la limite demandée."""
    for k in [1, 3, 5]:
        assert len(engine.find_flavor_pairings("leek", top_k=k, min_similarity=0.0)) <= k


def test_find_flavor_pairings_sorted(engine: FlavorChemistryEngine) -> None:
    """Vérifie que les pairages simples sont classés par score décroissant."""
    scores = [s for _, s in engine.find_flavor_pairings("leek", top_k=10, min_similarity=0.0)]
    assert scores == sorted(scores, reverse=True)


def test_unknown_ingredient_returns_empty(engine: FlavorChemistryEngine) -> None:
    """Vérifie qu'un ingrédient inconnu ne produit aucun pairage."""
    assert engine.find_flavor_pairings("ingredient_xyz_inconnu") == []


def test_high_threshold_returns_list(engine: FlavorChemistryEngine) -> None:
    """Vérifie qu'un seuil élevé ne change pas le type de retour."""
    assert isinstance(engine.find_flavor_pairings("garlic_oil", min_similarity=0.9999), list)


def test_load_embeddings_filters_and_normalizes(tmp_path: Path) -> None:
    """Vérifie le filtrage des nœuds, l'exclusion des vecteurs nuls et la normalisation."""
    embeddings_path = tmp_path / "embeddings.pkl"
    nodes_path = tmp_path / "nodes.csv"
    with embeddings_path.open("wb") as file:
        pickle.dump({"id1": [3.0, 4.0], "id2": [0.0, 0.0], "id3": [1.0, 0.0]}, file)
    with nodes_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["node_id", "node_type", "name"])
        writer.writerow(["id1", "ingredient", "Garlic"])
        writer.writerow(["id2", "ingredient", "Empty"])
        writer.writerow(["id3", "flavor", "Not an ingredient"])

    engine = FlavorChemistryEngine(embeddings_path, nodes_path)

    assert engine.ingredient_names() == ["garlic"]
    assert engine.get_ingredient_norm("garlic") == pytest.approx(5.0)
    assert engine.get_embedding("garlic") == pytest.approx(np.array([0.6, 0.8], dtype=np.float32))


def test_load_cleaned_embeddings_by_name(tmp_path: Path) -> None:
    """Vérifie le chargement d'embeddings nettoyés indexés par nom d'ingrédient."""
    embeddings_path = tmp_path / "cleaned_embeddings.pkl"
    nodes_path = tmp_path / "cleaned_nodes.csv"
    with embeddings_path.open("wb") as file:
        pickle.dump({"garlic oil": [0.6, 0.8]}, file)
    with nodes_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["node_id", "name"])
        writer.writerow(["42", "garlic oil"])

    engine = FlavorChemistryEngine(embeddings_path, nodes_path)

    assert engine.ingredient_names() == ["garlic oil"]
    assert engine.get_embedding("garlic_oil") == pytest.approx(np.array([0.6, 0.8], dtype=np.float32))


def test_ingredient_lookup_normalizes_names(synthetic_engine: FlavorChemistryEngine) -> None:
    """Vérifie la normalisation des espaces et de la casse lors d'une recherche."""
    assert synthetic_engine.get_ingredient_name("  GARLIC ") == "garlic"
    assert synthetic_engine.get_ingredient_name("unknown") is None


def test_ingredient_accessors_return_none_for_unknown(synthetic_engine: FlavorChemistryEngine) -> None:
    """Vérifie que les accesseurs de norme et d'embedding gèrent les noms inconnus."""
    assert synthetic_engine.get_ingredient_norm("unknown") is None
    assert synthetic_engine.get_embedding("unknown") is None


def test_find_flavor_pairings_excludes_source_and_applies_threshold(
    synthetic_engine: FlavorChemistryEngine,
) -> None:
    """Vérifie l'exclusion de la source et le filtrage par similarité minimale."""
    results = synthetic_engine.find_flavor_pairings("garlic", min_similarity=0.7)

    assert "garlic" not in [name for name, _ in results]
    assert [name for name, _ in results] == ["onion"]


def test_multi_pairings_shortlist_by_weighted_vector(synthetic_engine: FlavorChemistryEngine) -> None:
    """Vérifie le classement des candidats et leurs scores individuels par source."""
    combined, individual = synthetic_engine.find_multi_flavors_pairings(
        ["garlic", "basil"], top_k=1, min_similarity=0.0
    )

    assert [name for name, _ in combined] == ["onion"]
    assert [[name for name, _ in scores] for scores in individual] == [["onion"], ["onion"]]
    assert [scores[0][1] for scores in individual] == pytest.approx([0.8, 0.6])


def test_multi_pairings_respects_weights_and_threshold(synthetic_engine: FlavorChemistryEngine) -> None:
    """Vérifie que les poids influencent le vecteur de recherche et que le seuil filtre."""
    results, _ = synthetic_engine.find_multi_flavors_pairings(
        ["garlic", "basil"], top_k=1, min_similarity=0.94, weights=[3.0, 1.0]
    )
    filtered, _ = synthetic_engine.find_multi_flavors_pairings(["garlic", "basil"], top_k=1, min_similarity=0.99)

    assert [name for name, _ in results] == ["onion"]
    assert filtered == []


def test_multi_pairings_rejects_unknown_ingredients(synthetic_engine: FlavorChemistryEngine) -> None:
    """Vérifie que la recherche multi-ingrédients rejette un nom inconnu."""
    with pytest.raises(AssertionError, match="inconnus"):
        synthetic_engine.find_multi_flavors_pairings(["garlic", "unknown"])


def test_multi_pairings_rejects_mismatched_weights(synthetic_engine: FlavorChemistryEngine) -> None:
    """Vérifie que le nombre de poids correspond au nombre d'ingrédients."""
    with pytest.raises(AssertionError, match="poids"):
        synthetic_engine.find_multi_flavors_pairings(["garlic", "basil"], weights=[1.0])


def test_flavor_harmony_score_uses_mean_vector(synthetic_engine: FlavorChemistryEngine) -> None:
    """Vérifie le score d'harmonie pour des ingrédients orthogonaux."""
    assert synthetic_engine.flavor_harmony_score(["garlic", "basil"]) == pytest.approx(1 / np.sqrt(2))


def test_flavor_harmony_score_returns_zero_for_cancelling_vectors(
    synthetic_engine: FlavorChemistryEngine,
) -> None:
    """Vérifie qu'un vecteur moyen nul donne un score d'harmonie nul."""
    assert synthetic_engine.flavor_harmony_score(["garlic", "opposite"]) == 0.0


def test_get_ingredient_norm_known(engine: FlavorChemistryEngine) -> None:
    """Vérifie que la norme d'un ingrédient connu est un flottant positif."""
    mag = engine.get_ingredient_norm("garlic_oil")
    assert mag is not None and isinstance(mag, float) and mag > 0.0


def test_get_ingredient_norm_unknown(engine: FlavorChemistryEngine) -> None:
    """Vérifie que la norme d'un ingrédient inconnu vaut None."""
    assert engine.get_ingredient_norm("ingredient_xyz_inconnu") is None
