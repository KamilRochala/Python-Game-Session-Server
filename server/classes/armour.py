from pydantic import (
    BaseModel
)

from item import Item

class Armour(BaseModel, Item):
    defence_ammount: int # How much defence this armour gives
    max_health_increase: int # How much extra max health this armour gives