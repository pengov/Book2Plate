"""Script to sanitize FlavorGraph embeddings and node data."""

import csv
import pickle
import re

import numpy as np

from book2plate.config import settings

DATA_DIR = settings.references_dir
RAW_PKL = settings.flavorgraph_path
RAW_CSV = settings.flavorgraph_nodes_path

CLEAN_PKL = DATA_DIR / "flavorgraph_cleaned.pkl"
CLEAN_CSV = DATA_DIR / "nodes_cleaned.csv"

# Common non-food terms found in Recipe1M
EXCLUDED_PATTERNS = [
    r"\bpen\b",
    r"\bpin\b",
    r"\btoothpick\b",
    r"\bskewer\b",
    r"\bwrap\b",
    r"\bfoil\b",
    r"\bparchment\b",
    r"\bbag\b",
    r"\bbowl\b",
    r"\bpan\b",
    r"\bpot\b",
    r"\bwood\b",
    r"\bperoxide\b",
    r"\bmix\b",
    r"\bdinner_mix\b",
    r"\bdecorat\w*",
    r"\bicing\b",
    r"\bfrosting\b",
    r"\bpiping gel\b",
    r"\bfood colou?r\w*",
    r"\bfood dye\b",
    r"\bglitter\b",
    r"\bluster dust\b",
    r"\bsprinkle\w*",
    r"\bjimmies\b",
    r"\bnonpareil\w*",
    r"\bcandy\w*",
]

COMPILED_EXCLUSIONS = [re.compile(p, re.IGNORECASE) for p in EXCLUDED_PATTERNS]


def is_valid_food_item(name: str) -> bool:
    clean = name.strip().lower()
    if len(clean) < 3:
        return False
    for pattern in COMPILED_EXCLUSIONS:
        if pattern.search(clean):
            return False
    return True


def clean_dataset():
    # Load the CSV
    nodes_info = {}
    with open(RAW_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            node_id = int(row["node_id"])
            name = row["name"].strip().lower().replace("_", " ")
            nodes_info[node_id] = {"name": name, "node_type": row["node_type"]}
    print(f"Total initial nodes in CSV: {len(nodes_info):,}")

    # Load the embeddings pickle
    with open(RAW_PKL, "rb") as f:
        raw_embeddings = pickle.load(f)

    # Combined filtering
    cleaned_embeddings = {}
    cleaned_nodes = []
    removed_non_food = []

    for raw_id, vec in raw_embeddings.items():
        node_id = int(raw_id)
        if node_id not in nodes_info:
            continue

        meta = nodes_info[node_id]
        name = meta["name"].strip().lower().replace("_", " ")

        # Remove chemical compounds
        if meta["node_type"] != "ingredient":
            continue

        # Remove equipment and anomalies
        if not is_valid_food_item(name):
            removed_non_food.append(name)
            continue

        vector = np.array(vec, dtype=np.float32)
        norm = float(np.linalg.norm(vector))

        if norm > 0:
            cleaned_embeddings[name] = vector / norm
            cleaned_nodes.append({
                "node_id": node_id,
                "name": name,
            })

    print(f"Nodes removed (chemical compounds): ~1650")
    print(f"Nodes removed (noise / equipment / anomalies): {len(removed_non_food)}")
    print(f"Sample removed items: {removed_non_food[:15]}")
    print(f"Food ingredients kept: {len(cleaned_embeddings)}")

    # Save cleaned artifacts
    with open(CLEAN_PKL, "wb") as f:
        pickle.dump(cleaned_embeddings, f)

    with open(CLEAN_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["node_id", "name"])
        writer.writeheader()
        writer.writerows(cleaned_nodes)

    print(f"Cleaned embeddings saved: {CLEAN_PKL}")
    print(f"Cleaned index saved: {CLEAN_CSV}")


if __name__ == "__main__":
    clean_dataset()