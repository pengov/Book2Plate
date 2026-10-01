from pydantic import BaseModel, Field
from typing import List, Optional
from book2plate.core.enums import UnitEnum, CourseType, DietaryConstraint


class IngredientItem(BaseModel):
    name: str = Field(description="Nom normalisé de l'ingrédient en minuscules")
    quantity: float = Field(gt=0, description="Quantité strictly positive")
    unit: UnitEnum = Field(default=UnitEnum.PIECE)
    category: Optional[str] = Field(default=None, description="Rayon (ex: fruits_legumes, epicerie)")
    substitute_for: Optional[str] = Field(
        default=None, description="Nom de l'ingrédient original si c'est un substitut"
    )


class CookingStep(BaseModel):
    step_number: int = Field(ge=1)
    instruction: str = Field(min_length=5)
    duration_minutes: Optional[int] = Field(default=None, ge=0)


class NutritionInfo(BaseModel):
    calories_kcal: float = Field(ge=0)
    proteins_g: float = Field(ge=0)
    carbs_g: float = Field(ge=0)
    fats_g: float = Field(ge=0)
    fiber_g: Optional[float] = Field(default=0.0, ge=0)


class RecipeSchema(BaseModel):
    title: str = Field(min_length=2)
    source: str = Field(description="Livre d'origine, page, ou URL Instagram")
    course_type: CourseType = Field(default=CourseType.MAIN)
    prep_time_minutes: int = Field(ge=0)
    cook_time_minutes: int = Field(ge=0)
    servings: int = Field(ge=1)
    ingredients: List[IngredientItem] = Field(min_length=1)
    steps: List[CookingStep] = Field(min_length=1)
    dietary_tags: List[DietaryConstraint] = Field(default_factory=list)

    # Métadonnées calculées déterministement (Bloc 2)
    estimated_cost_cents: Optional[int] = Field(
        default=None, ge=0, description="Coût estimé en centimes"
    )
    nutrition: Optional[NutritionInfo] = None

    @property
    def total_time_minutes(self) -> int:
        return self.prep_time_minutes + self.cook_time_minutes