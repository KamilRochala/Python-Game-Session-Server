from pydantic import (
    BaseModel
)

from item import Item

class Accessory(BaseModel, Item):
    what_stat_is_multiplied: str # For example "dmg" will increase the damage of the player
    base_stat_multuplier: float # This is the base multiplier of the accesory, so it is affected by the floor multiplier