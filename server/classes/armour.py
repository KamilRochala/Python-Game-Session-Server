from pydantic import (
    BaseModel
)

from .item import Item

class Armour(Item):
    defence_ammount: float # How much defence this armour gives
    max_health_increase: float # How much extra max health this armour gives