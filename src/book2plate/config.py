from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = (
        "postgresql+psycopg://book2plate_user:book2plate_secure_password@localhost:5432/book2plate_db"
    )

    base_dir: Path = Path(__file__).resolve().parent.parent.parent
    references_dir: Path = base_dir / "data" / "references"

    flavorgraph_path: Path = references_dir / "flavorgraph_embeddings.pkl"
    flavorgraph_nodes_path: Path = references_dir / "nodes_191120.csv"
    flavorgraph_cleaned_path: Path = references_dir / "flavorgraph_cleaned.pkl"
    flavorgraph_nodes_cleaned_path: Path = references_dir / "nodes_cleaned.csv"
    open_prices_path: Path = references_dir / "open_prices.parquet"
    ciqual_path: Path = references_dir / "ciqual_2020.csv"
    wine_pairing_path: Path = references_dir / "wine_pairing_rules.json"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()