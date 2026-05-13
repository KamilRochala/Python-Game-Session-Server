from .item import Item
from enum import Enum

from pydantic import (
    field_validator,
    model_validator
)

class WeaponType(str, Enum):
    KNIGHT = "knight"
    CLERIC = "cleric"

class Weapon(Item):
    damage: float
    healing_capacity: float
    weapon_type: WeaponType

    @field_validator('damage')
    @classmethod
    def validate_damage(cls, v):
        if v <= 0:
            raise ValueError('damage cannot be less or equal to 0')
        return v

    @field_validator('healing_capacity')
    @classmethod
    def validate_healing_capacity_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError('healing stat must be 0 or positive')
        return v

    @model_validator(mode='after')
    def validate_cross_fields(self):
        if self.healing_capacity > 0 and self.weapon_type == WeaponType.KNIGHT:
            raise ValueError('Knights cannot use healing weapons')
        return self