from pathlib import Path
from typing import Optional
import duckdb

from book2plate.config import settings


class GroceryPricingEngine:
    """Deterministic budget estimation engine based on Open Prices via DuckDB."""

    def __init__(self, parquet_path: Optional[Path] = None) -> None:
        self.parquet_path = parquet_path or settings.open_prices_path
        self._con = duckdb.connect(database=":memory:")
        self._table_available = False
        self._init_db()

    def _init_db(self) -> None:
        """Checks whether the Parquet file exists and prepares the DuckDB view."""
        if not self.parquet_path.exists():
            return

        # Create a DuckDB view pointing directly to the Parquet file
        escaped_path = str(self.parquet_path).replace("\\", "/")
        try:
            self._con.execute(f"""
                CREATE VIEW IF NOT EXISTS prices_view AS 
                SELECT * FROM read_parquet('{escaped_path}')
            """)
            self._table_available = True
        except Exception:
            self._table_available = False

    @property
    def is_available(self) -> bool:
        return self._table_available

    def get_median_price_per_kg(self, ingredient_name: str) -> Optional[float]:
        """
        Calculates the median price per kilogram (€/kg) for a given ingredient.
        Searches by category tag or label in EUR records.
        """
        if not self._table_available:
            return None

        clean_term = ingredient_name.strip().lower().replace("_", " ")

        query = """
            SELECT median(price) AS median_price
            FROM prices_view
            WHERE currency = 'EUR'
              AND price > 0
              AND price < 100
              AND (
                lower(category_tag) LIKE '%' || ? || '%'
                OR lower(category_tag) LIKE '%' || replace(?, ' ', '-') || '%'
              )
        """

        try:
            result = self._con.execute(query, [clean_term, clean_term]).fetchone()
            if result and result[0] is not None:
                return round(float(result[0]), 2)
        except Exception:
            pass

        return None

    def estimate_ingredient_cost_cents(
        self,
        ingredient_name: str,
        quantity_g: float,
        fallback_price_per_kg: float = 3.50,
    ) -> int:
        """
        Estimates the cost of an ingredient in euro cents based on its mass in grams.
        Uses an average fallback price if the food has no matching record.
        """
        if quantity_g <= 0:
            return 0

        price_per_kg = self.get_median_price_per_kg(ingredient_name)

        if price_per_kg is None:
            price_per_kg = fallback_price_per_kg

        # Cost in euros = (quantity in kg) * (price per kg)
        cost_eur = (quantity_g / 1000.0) * price_per_kg
        return max(1, int(round(cost_eur * 100)))