import csv
import pickle
from pathlib import Path

import numpy as np
import pytest

from book2plate.config import settings
from book2plate.deterministic.chemistry import FlavorChemistryEngine


@pytest.fixture(scope="module")
def engine() -> FlavorChemistryEngine:
    """Loads FlavorGraph for tests that verify the reference data."""
    if not settings.flavorgraph_path.exists() or not settings.flavorgraph_nodes_path.exists():
        pytest.skip("FlavorGraph files missing from data/references/")
    return FlavorChemistryEngine()


@pytest.fixture
def synthetic_engine() -> FlavorChemistryEngine:
    """Builds an in-memory engine with four deterministic unit embeddings."""
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
    """Verifies that the reference FlavorGraph dataset contains enough ingredients."""
    assert engine.total_ingredients > 500


def test_ingredient_names_are_text(engine: FlavorChemistryEngine) -> None:
    """Verifies that loaded names are non-empty text strings."""
    for name in engine.ingredient_names()[:50]:
        assert isinstance(name, str) and name and not name.isdigit()


def test_known_ingredients_present(engine: FlavorChemistryEngine) -> None:
    """Verifies that a set of expected ingredients are present in FlavorGraph."""
    known = {"garlic oil", "leek", "zucchini", "onion"}
    missing = known - set(engine.ingredient_names())
    assert not missing, f"Missing ingredients: {missing}"


def test_find_flavor_pairings_returns_list(engine: FlavorChemistryEngine) -> None:
    """Verifies that the simple search returns a list."""
    assert isinstance(engine.find_flavor_pairings("garlic_oil", top_k=3), list)


def test_find_flavor_pairings_format(engine: FlavorChemistryEngine) -> None:
    """Verifies the format and domain of pairing scores."""
    results = engine.find_flavor_pairings("garlic_oil", top_k=3, min_similarity=0.0)
    assert len(results) > 0
    name, score = results[0]
    assert isinstance(name, str) and not name.isdigit()
    assert 0.0 <= score <= 1.0


def test_find_flavor_pairings_top_k(engine: FlavorChemistryEngine) -> None:
    """Verifies that the simple search does not exceed the requested limit."""
    for k in [1, 3, 5]:
        assert len(engine.find_flavor_pairings("leek", top_k=k, min_similarity=0.0)) <= k


def test_find_flavor_pairings_sorted(engine: FlavorChemistryEngine) -> None:
    """Verifies that simple pairings are sorted in descending order."""
    scores = [s for _, s in engine.find_flavor_pairings("leek", top_k=10, min_similarity=0.0)]
    assert scores == sorted(scores, reverse=True)


def test_unknown_ingredient_returns_empty(engine: FlavorChemistryEngine) -> None:
    """Verifies that an unknown ingredient produces no pairings."""
    assert engine.find_flavor_pairings("ingredient_xyz_unknown") == []


def test_high_threshold_returns_list(engine: FlavorChemistryEngine) -> None:
    """Verifies that a high threshold does not change the return type."""
    assert isinstance(engine.find_flavor_pairings("garlic_oil", min_similarity=0.9999), list)


def test_load_embeddings_filters_and_normalizes(tmp_path: Path) -> None:
    """Verifies node filtering, exclusion of zero vectors, and normalization."""
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
    """Verifies loading of cleaned embeddings indexed by ingredient name."""
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
    """Verifies whitespace and case normalization during a lookup."""
    assert synthetic_engine.get_ingredient_name("  GARLIC ") == "garlic"
    assert synthetic_engine.get_ingredient_name("unknown") is None


def test_ingredient_accessors_return_none_for_unknown(synthetic_engine: FlavorChemistryEngine) -> None:
    """Verifies that norm and embedding accessors handle unknown names gracefully."""
    assert synthetic_engine.get_ingredient_norm("unknown") is None
    assert synthetic_engine.get_embedding("unknown") is None


def test_find_flavor_pairings_excludes_source_and_applies_threshold(
    synthetic_engine: FlavorChemistryEngine,
) -> None:
    """Verifies source exclusion and minimum similarity filtering."""
    results = synthetic_engine.find_flavor_pairings("garlic", min_similarity=0.7)

    assert "garlic" not in [name for name, _ in results]
    assert [name for name, _ in results] == ["onion"]


def test_multi_pairings_shortlist_by_weighted_vector(synthetic_engine: FlavorChemistryEngine) -> None:
    """Verifies candidate ranking and individual scores per source ingredient."""
    combined, individual = synthetic_engine.find_multi_flavors_pairings(
        ["garlic", "basil"], top_k=1, min_similarity=0.0
    )

    assert [name for name, _ in combined] == ["onion"]
    assert [[name for name, _ in scores] for scores in individual] == [["onion"], ["onion"]]
    assert [scores[0][1] for scores in individual] == pytest.approx([0.8, 0.6])


def test_multi_pairings_respects_weights_and_threshold(synthetic_engine: FlavorChemistryEngine) -> None:
    """Verifies that weights influence the search vector and that the threshold filters results."""
    results, _ = synthetic_engine.find_multi_flavors_pairings(
        ["garlic", "basil"], top_k=1, min_similarity=0.94, weights=[3.0, 1.0]
    )
    filtered, _ = synthetic_engine.find_multi_flavors_pairings(["garlic", "basil"], top_k=1, min_similarity=0.99)

    assert [name for name, _ in results] == ["onion"]
    assert filtered == []


def test_multi_pairings_rejects_unknown_ingredients(synthetic_engine: FlavorChemistryEngine) -> None:
    """Verifies that the multi-ingredient search rejects an unknown name."""
    with pytest.raises(AssertionError, match="unknown"):
        synthetic_engine.find_multi_flavors_pairings(["garlic", "unknown"])


def test_multi_pairings_rejects_mismatched_weights(synthetic_engine: FlavorChemistryEngine) -> None:
    """Verifies that the number of weights must match the number of ingredients."""
    with pytest.raises(AssertionError, match="weights"):
        synthetic_engine.find_multi_flavors_pairings(["garlic", "basil"], weights=[1.0])


def test_flavor_harmony_score_uses_mean_vector(synthetic_engine: FlavorChemistryEngine) -> None:
    """Verifies the harmony score for orthogonal ingredients."""
    assert synthetic_engine.flavor_harmony_score(["garlic", "basil"]) == pytest.approx(1 / np.sqrt(2))


def test_flavor_harmony_score_returns_zero_for_cancelling_vectors(
    synthetic_engine: FlavorChemistryEngine,
) -> None:
    """Verifies that a zero mean vector yields a harmony score of zero."""
    assert synthetic_engine.flavor_harmony_score(["garlic", "opposite"]) == 0.0


def test_get_ingredient_norm_known(engine: FlavorChemistryEngine) -> None:
    """Verifies that the norm of a known ingredient is a positive float."""
    mag = engine.get_ingredient_norm("garlic_oil")
    assert mag is not None and isinstance(mag, float) and mag > 0.0


def test_get_ingredient_norm_unknown(engine: FlavorChemistryEngine) -> None:
    """Verifies that the norm of an unknown ingredient is None."""
    assert engine.get_ingredient_norm("ingredient_xyz_unknown") is None
