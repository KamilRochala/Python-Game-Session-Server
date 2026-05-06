from pydantic import (
    BaseModel
)

from item import Item

class Weapon(BaseModel, Item):
    damage: int # The damage of the weapon
    healing_capacity: int # This should only be for clerics, the higher the number, the higher the ammount of health will be restored
