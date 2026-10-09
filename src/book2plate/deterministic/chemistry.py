"""Deterministic ingredient substitution engine based on FlavorGraph."""

import csv
import json
import pickle
from pathlib import Path

import numpy as np

from book2plate.config import settings


class FlavorChemistryEngine:
    """Computes ingredient substitutes via cosine similarity on 300D FlavorGraph embeddings."""

    def __init__(
        self,
        embeddings_path: Path | None = None,
        nodes_path: Path | None = None,
        alias_map_path: Path | None = None,
    ) -> None:
        self.embeddings_path = embeddings_path or settings.flavorgraph_cleaned_path
        self.nodes_path = nodes_path or settings.flavorgraph_nodes_cleaned_path
        self.alias_map_path = alias_map_path or settings.alias_map_path

        self._embeddings: dict[str, np.ndarray] = {}  # name -> normalized vector
        self._norms: dict[str, float] = {}  # name -> original L2 norm
        self._alias_map: dict[str, str] = {}  # alias -> canonical name

        self._load_embeddings()

    def _load_embeddings(self) -> None:
        """Loads raw embeddings by node ID or cleaned embeddings indexed by ingredient name."""
        if not self.embeddings_path.exists():
            raise FileNotFoundError(f"FlavorGraph file not found: {self.embeddings_path}")
        if not self.nodes_path.exists():
            raise FileNotFoundError(f"Mapping CSV file not found: {self.nodes_path}")

        with open(self.embeddings_path, "rb") as f:
            raw: dict[str, np.ndarray] = pickle.load(f)

        id_to_name: dict[str, str] = {}
        valid_names: set[str] = set()
        original_norms: dict[str, float] = {}
        with open(self.nodes_path, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                node_type = row.get("node_type", "").strip().lower().replace("_", " ")
                if node_type and node_type != "ingredient":
                    continue
                name = row["name"].strip().lower().replace("_", " ")
                valid_names.add(name)
                node_id = row.get("node_id")
                if node_id:
                    id_to_name[node_id] = name
                if row.get("norm"):
                    original_norms[name] = float(row["norm"])

        for raw_key, vec in raw.items():
            name = id_to_name.get(str(raw_key))
            if name is None:
                candidate_name = str(raw_key).strip().lower().replace("_", " ")
                if candidate_name not in valid_names:
                    continue
                name = candidate_name
            arr = np.asarray(vec, dtype=np.float32)
            norm = float(np.linalg.norm(arr))
            if norm > 0:
                self._embeddings[name] = arr / norm
                self._norms[name] = original_norms.get(name, norm)

        if self.alias_map_path and self.alias_map_path.exists():
            try:
                with open(self.alias_map_path, "r", encoding="utf-8") as f:
                    self._alias_map = json.load(f)
            except Exception:
                self._alias_map = {}

    def _metric(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Returns the dot product of two already-normalized embeddings, equivalent to cosine similarity."""
        return float(np.dot(vec1, vec2))

    @property
    def total_ingredients(self) -> int:
        """Returns the number of loaded ingredients."""
        return len(self._embeddings)

    def ingredient_names(self) -> list[str]:
        """Returns the normalized names of all loaded ingredients."""
        return list(self._embeddings.keys())

    def get_ingredient_name(self, ingredient_name: str) -> str | None:
        """Normalizes a name, resolves aliases if present, and returns the canonical name if known."""
        assert ingredient_name, "Ingredient name cannot be empty."
        raw_lower = ingredient_name.lower().strip()

        alias_map = getattr(self, "_alias_map", {})
        # Check alias map (raw string, spaces, or underscores)
        target = alias_map.get(raw_lower) or alias_map.get(raw_lower.replace("_", " "))
        if target:
            raw_lower = target.lower().strip()

        normalized_name = raw_lower.replace("_", " ")
        if normalized_name in self._norms or normalized_name in self._embeddings:
            return normalized_name
        if raw_lower in self._norms or raw_lower in self._embeddings:
            return raw_lower
        return None

    def get_ingredient_names(self, ingredient_names: list[str]) -> list[str]:
        """Normalizes a list of names and keeps only the known ingredients."""
        return [name for name in (self.get_ingredient_name(n) for n in ingredient_names) if name is not None]

    def get_ingredient_norm(self, ingredient_name: str) -> float | None:
        """Returns the original L2 norm of a known ingredient, or None if unknown."""
        return self._norms.get(self.get_ingredient_name(ingredient_name))

    def get_embedding(self, ingredient_name: str) -> np.ndarray | None:
        """Returns the normalized embedding of a known ingredient, or None if unknown."""
        return self._embeddings.get(self.get_ingredient_name(ingredient_name))

    def find_flavor_pairings(
        self,
        ingredient_name: str,
        top_k: int = 0,
        min_similarity: float = 0.0,
    ) -> list[tuple[str, float]]:
        """
        Returns the closest ingredients by cosine similarity.

        `top_k=0` returns all results above the threshold; an unknown ingredient
        produces an empty list.
        """
        assert top_k >= 0, "top_k must be a non-negative integer."
        assert 0.0 <= min_similarity < 1.0, "min_similarity must be between 0 and 1."
        target = self.get_ingredient_name(ingredient_name)
        if not target:
            return []

        target_vec = self._embeddings[target]
        scores = [(name, self._metric(target_vec, vec)) for name, vec in self._embeddings.items() if name != target]
        scores = [(n, float(s)) for n, s in scores if s >= min_similarity]
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[: top_k if top_k else len(scores)]

    def find_multi_flavors_pairings(
        self,
        ingredient_names: list[str],
        top_k: int = 0,
        min_similarity: float = 0.0,
        weights: list[float] | None = None,
    ) -> tuple[list[tuple[str, float]], list[list[tuple[str, float]]]]:
        """
        Ranks candidates by proximity to the weighted average vector of the ingredients.

        Returns ranked candidates and their individual scores per source ingredient.
        `top_k=0` keeps all candidates above the threshold.
        """
        assert len(ingredient_names) >= 2, "The ingredient list must contain at least two elements."
        assert weights is None or len(weights) == len(ingredient_names), (
            "The weights list must match the ingredient list."
        )
        assert top_k >= 0, "top_k must be a non-negative integer."
        assert 0.0 <= min_similarity < 1.0, "min_similarity must be between 0 and 1."

        known_names = self.get_ingredient_names(ingredient_names)
        assert len(known_names) == len(ingredient_names), "Some ingredients in the list are unknown."
        ingredient_names = known_names

        if weights is None:
            normalized_weights = np.full(len(ingredient_names), 1.0 / len(ingredient_names), dtype=np.float16)
        else:
            normalized_weights = np.asarray(weights, dtype=np.float16)
            total_weight = float(normalized_weights.sum())
            normalized_weights /= total_weight
            assert np.all(normalized_weights > 0), "All weights must be strictly positive."

        ingredient_vectors = np.stack([self._embeddings[name] for name in ingredient_names])
        weighted_vector = normalized_weights @ ingredient_vectors
        weighted_norm = float(np.linalg.norm(weighted_vector))
        assert weighted_norm > 0, "The weighted ingredient vector cannot be zero."
        weighted_vector /= weighted_norm

        source_names = set(ingredient_names)
        candidates = [
            (name, self._metric(weighted_vector, vector))
            for name, vector in self._embeddings.items()
            if name not in source_names
        ]
        candidates = [(name, float(score)) for name, score in candidates if score >= min_similarity]
        candidates.sort(key=lambda item: item[1], reverse=True)
        if top_k:
            candidates = candidates[: top_k if top_k else len(candidates)]

        individual_scores = []
        for source in ingredient_names:
            source_scores = []
            for name, _ in candidates:
                score = self._metric(self._embeddings[source], self._embeddings[name])
                if score >= min_similarity:
                    source_scores.append((name, score))
            individual_scores.append(source_scores)

        return candidates, individual_scores

    def flavor_harmony_score(self, ingredient_names: list[str], weights: list[float] | None = None) -> float:
        """
        Computes the average similarity of ingredients against their weighted mean vector.

        Returns 0.0 if the mean vector is zero.
        """
        assert len(ingredient_names) >= 2, "The ingredient list must contain at least two elements."
        assert weights is None or len(weights) == len(ingredient_names), (
            "The weights list must match the ingredient list."
        )

        if weights is None:
            normalized_weights = np.full(len(ingredient_names), 1.0 / len(ingredient_names), dtype=np.float16)
        else:
            normalized_weights = np.asarray(weights, dtype=np.float16)
            total_weight = float(normalized_weights.sum())
            normalized_weights /= total_weight

        ingredient_vectors = np.stack([self._embeddings[name] for name in ingredient_names])
        weighted_vector = normalized_weights @ ingredient_vectors
        weighted_norm = float(np.linalg.norm(weighted_vector))
        if weighted_norm == 0:
            return 0.0
        weighted_vector /= weighted_norm

        score = np.sum([self._metric(weighted_vector, self._embeddings[name]) for name in ingredient_names]) / len(
            ingredient_names
        )
        return score


if __name__ == "__main__":
    engine = FlavorChemistryEngine()
    print(f"Loaded ingredients: {engine.total_ingredients}")

    ingredient = "garlic"
    subs = engine.find_flavor_pairings(ingredient, top_k=5, min_similarity=0.3)
    if subs:
        print(f"\nPairings for '{ingredient}':")
        for name, score in subs:
            print(f"  {name:45s} {score:.4f}")
    else:
        print(f"\n'{ingredient}': not found.")

    print()

    ingredients = ["chocolate", "flour"]
    multi_subs, individual_scores = engine.find_multi_flavors_pairings(ingredients, top_k=5, min_similarity=0.3)
    if multi_subs:
        print(f"Pairings for {ingredients}:")
        for name, score in multi_subs:
            print(f"  {name:20s} {score:.3f}")
    else:
        print(f"\n{ingredients}: not found.")

    print()
    harmony_score = engine.flavor_harmony_score(ingredients)
    print(f"Harmony score for {ingredients}: {harmony_score:.3f}")
