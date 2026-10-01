"""Moteur déterministe de substitution d'ingrédients basé sur FlavorGraph."""

import csv
import pickle
from pathlib import Path

import numpy as np

from book2plate.config import settings


class FlavorChemistryEngine:
    """Calcule des substituts d'ingrédients par similarité cosinus sur les embeddings FlavorGraph 300D."""

    def __init__(
        self,
        embeddings_path: Path | None = None,
        nodes_path: Path | None = None,
    ) -> None:
        """Initialise le moteur et charge les embeddings depuis les chemins fournis ou la configuration."""
        self.embeddings_path = embeddings_path or settings.flavorgraph_cleaned_path
        self.nodes_path = nodes_path or settings.flavorgraph_nodes_cleaned_path

        self._embeddings: dict[str, np.ndarray] = {}  # name -> vecteur normalisé
        self._norms: dict[str, float] = {}  # name -> norme L2 originale

        self._load_embeddings()

    def _load_embeddings(self) -> None:
        """Charge les embeddings bruts par ID ou nettoyés par nom d'ingrédient."""
        if not self.embeddings_path.exists():
            raise FileNotFoundError(f"Fichier FlavorGraph introuvable : {self.embeddings_path}")
        if not self.nodes_path.exists():
            raise FileNotFoundError(f"Fichier CSV de mapping introuvable : {self.nodes_path}")

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

    def _metric(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calcule le produit scalaire de deux embeddings déjà normalisés, équivalent au cosinus."""
        return float(np.dot(vec1, vec2))

    @property
    def total_ingredients(self) -> int:
        """Retourne le nombre d'ingrédients chargés."""
        return len(self._embeddings)

    def ingredient_names(self) -> list[str]:
        """Retourne les noms normalisés de tous les ingrédients chargés."""
        return list(self._embeddings.keys())

    def get_ingredient_name(self, ingredient_name: str) -> str | None:
        """Normalise un nom et le retourne s'il est connu, sinon retourne None."""
        assert ingredient_name, "Le nom de l'ingrédient ne peut pas être vide."
        normalized_name = ingredient_name.lower().strip().replace("_", " ")
        if normalized_name in self._norms:
            return normalized_name

    def get_ingredient_names(self, ingredient_names: list[str]) -> list[str]:
        """Normalise une liste de noms et conserve uniquement les ingrédients connus."""
        return [name for name in (self.get_ingredient_name(n) for n in ingredient_names) if name is not None]

    def get_ingredient_norm(self, ingredient_name: str) -> float | None:
        """Retourne la norme L2 d'origine d'un ingrédient connu, ou None s'il est inconnu."""
        return self._norms.get(self.get_ingredient_name(ingredient_name))

    def get_embedding(self, ingredient_name: str) -> np.ndarray | None:
        """Retourne l'embedding normalisé d'un ingrédient connu, ou None s'il est inconnu."""
        return self._embeddings.get(self.get_ingredient_name(ingredient_name))

    def find_flavor_pairings(
        self,
        ingredient_name: str,
        top_k: int = 0,
        min_similarity: float = 0.0,
    ) -> list[tuple[str, float]]:
        """
        Retourne les ingrédients les plus proches par similarité cosinus.

        `top_k=0` retourne tous les résultats au-dessus du seuil ; un ingrédient inconnu
        produit une liste vide.
        """
        assert top_k >= 0, "top_k doit être un entier positif."
        assert 0.0 <= min_similarity < 1.0, "min_similarity doit être entre 0 et 1."
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
        Classe les candidats par proximité au vecteur moyen pondéré des ingrédients.

        Retourne les candidats classés et leurs scores individuels par ingrédient source.
        `top_k=0` conserve tous les candidats au-dessus du seuil.
        """
        assert len(ingredient_names) >= 2, "La liste d'ingrédients doit contenir au moins deux éléments."
        assert weights is None or len(weights) == len(ingredient_names), (
            "La liste de poids doit correspondre à la liste d'ingrédients."
        )
        assert top_k >= 0, "top_k doit être un entier positif."
        assert 0.0 <= min_similarity < 1.0, "min_similarity doit être entre 0 et 1."

        known_names = self.get_ingredient_names(ingredient_names)
        assert len(known_names) == len(ingredient_names), "Certains ingrédients de la liste sont inconnus."
        ingredient_names = known_names

        if weights is None:
            normalized_weights = np.full(len(ingredient_names), 1.0 / len(ingredient_names), dtype=np.float16)
        else:
            normalized_weights = np.asarray(weights, dtype=np.float16)
            total_weight = float(normalized_weights.sum())
            normalized_weights /= total_weight
            assert np.all(normalized_weights > 0), "Les poids doivent être strictement positifs."

        ingredient_vectors = np.stack([self._embeddings[name] for name in ingredient_names])
        weighted_vector = normalized_weights @ ingredient_vectors
        weighted_norm = float(np.linalg.norm(weighted_vector))
        assert weighted_norm > 0, "Le vecteur pondéré des ingrédients ne peut pas être nul."
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
        Calcule la similarité moyenne des ingrédients avec leur vecteur moyen pondéré.

        Retourne 0.0 si ce vecteur moyen est nul.
        """
        assert len(ingredient_names) >= 2, "La liste d'ingrédients doit contenir au moins deux éléments."
        assert weights is None or len(weights) == len(ingredient_names), (
            "La liste de poids doit correspondre à la liste d'ingrédients."
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
    print(f"Ingrédients chargés : {engine.total_ingredients}")

    ingredient = "garlic"
    subs = engine.find_flavor_pairings(ingredient, top_k=5, min_similarity=0.3)
    if subs:
        print(f"\nPairages pour '{ingredient}':")
        for name, score in subs:
            print(f"  {name:45s} {score:.4f}")
    else:
        print(f"\n'{ingredient}' : non trouvé.")

    print()

    ingredients = ["chocolate", "flour"]
    multi_subs, individual_scores = engine.find_multi_flavors_pairings(ingredients, top_k=5, min_similarity=0.3)
    if multi_subs:
        print(f"Pairages pour {ingredients}:")
        for name, score in multi_subs:
            print(f"  {name:20s} {score:.3f}")
    else:
        print(f"\n{ingredients} : non trouvés.")

    print()
    harmony_score = engine.flavor_harmony_score(ingredients)
    print(f"Score d'harmonie pour {ingredients}: {harmony_score:.3f}")
