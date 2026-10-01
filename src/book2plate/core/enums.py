from enum import Enum


class UnitEnum(str, Enum):
    GRAM = "g"
    KILOGRAM = "kg"
    MILLILITER = "ml"
    CENTILITER = "cl"
    LITER = "l"
    PIECE = "piece"
    TABLESPOON = "c_a_s"
    TEASPOON = "c_a_c"
    PINCH = "pincee"


class CourseType(str, Enum):
    STARTER = "entree"
    MAIN = "plat"
    DESSERT = "dessert"
    SIDE = "accompagnement"


class DietaryConstraint(str, Enum):
    VEGETARIAN = "vegetarien"
    VEGAN = "vegan"
    GLUTEN_FREE = "sans_gluten"
    LACTOSE_FREE = "sans_lactose"
    NUT_FREE = "sans_fruits_a_coque"