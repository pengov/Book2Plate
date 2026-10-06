import pytest
from book2plate.config import settings
from book2plate.deterministic.pricing import GroceryPricingEngine


@pytest.fixture(scope="module")
def pricing_engine():
    if not settings.open_prices_path.exists():
        pytest.skip("open_prices.parquet missing from data/references/")
    return GroceryPricingEngine()


def test_pricing_engine_initialization(pricing_engine):
    """Verifies that DuckDB initializes and can access the Parquet file."""
    assert pricing_engine.is_available is True


def test_estimate_ingredient_cost_standard(pricing_engine):
    """Verifies cost calculation for a given quantity (e.g. 250 g of flour/butter)."""
    # 250 grams of flour or a standard ingredient
    cost_cents = pricing_engine.estimate_ingredient_cost_cents("flour", quantity_g=250.0)

    assert isinstance(cost_cents, int)
    assert cost_cents > 0  # Must be greater than 0 cents
    assert cost_cents < 500  # Must remain realistic (< €5.00 for 250 g)


def test_estimate_zero_quantity_returns_zero(pricing_engine):
    """Verifies that a zero or negative quantity returns 0 cents."""
    assert pricing_engine.estimate_ingredient_cost_cents("flour", quantity_g=0.0) == 0
    assert pricing_engine.estimate_ingredient_cost_cents("flour", quantity_g=-50.0) == 0


def test_fallback_price_used_for_unknown_ingredient(pricing_engine):
    """Verifies that the fallback price is used for an unknown product."""
    # Test with a specific fallback of €10/kg for 500 g -> should give exactly 500 cents (€5.00)
    cost_cents = pricing_engine.estimate_ingredient_cost_cents(
        "totally_unknown_ingredient_xyz", quantity_g=500.0, fallback_price_per_kg=10.0
    )
    assert cost_cents == 500