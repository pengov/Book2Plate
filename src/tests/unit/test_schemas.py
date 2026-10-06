import pytest
from pydantic import ValidationError
from book2plate.core.schemas import RecipeSchema, IngredientItem, CookingStep
from book2plate.core.enums import UnitEnum, CourseType, DietaryConstraint


def test_recipe_schema_valid():
    recipe = RecipeSchema(
        title="Risotto Verde",
        source="Italie Simplissime, p.42",
        course_type=CourseType.MAIN,
        prep_time_minutes=10,
        cook_time_minutes=20,
        servings=2,
        ingredients=[
            IngredientItem(name="arborio rice", quantity=160, unit=UnitEnum.GRAM),
            IngredientItem(name="fresh spinach", quantity=200, unit=UnitEnum.GRAM),
            IngredientItem(name="parmesan", quantity=40, unit=UnitEnum.GRAM),
        ],
        steps=[
            CookingStep(step_number=1, instruction="Toast the rice in a little oil.", duration_minutes=3),
            CookingStep(step_number=2, instruction="Add broth and stir in the spinach.", duration_minutes=17),
        ],
        dietary_tags=[DietaryConstraint.VEGETARIAN],
    )

    assert recipe.total_time_minutes == 30
    assert len(recipe.ingredients) == 3
    assert recipe.ingredients[0].unit == UnitEnum.GRAM


def test_recipe_schema_rejects_negative_quantity():
    with pytest.raises(ValidationError):
        IngredientItem(name="salt", quantity=-5, unit=UnitEnum.GRAM)


def test_recipe_schema_requires_steps():
    with pytest.raises(ValidationError):
        RecipeSchema(
            title="Empty Recipe",
            source="Test",
            prep_time_minutes=5,
            cook_time_minutes=5,
            servings=1,
            ingredients=[IngredientItem(name="water", quantity=100, unit=UnitEnum.MILLILITER)],
            steps=[],  # Must fail because min_length=1
        )


if __name__ == "__main__":
    pytest.main([__file__])