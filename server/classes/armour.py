from pydantic import (
    BaseModel, field_validator
)

from .item import Item

class Armour(Item):
    defence_ammount: int # How much defence this armour gives
    max_health_increase: int # How much extra max health this armour gives

    @field_validator('defence_ammount')
    def validate_defence(cls, v):
        if v < 0:
            raise ValueError('Defence amount cannot be negative')
        return v