import random

from pydantic import (
    BaseModel,
    field_validator
)

class Enemy(BaseModel):
    max_hp: float
    current_hp: float
    room_number: int
    damage: float
    armour: int

    @field_validator('max_hp')
    @classmethod
    def validate_max_hp(cls, v):
        if v <= 0:
            raise ValueError('max_hp must be greater than 0')
        return v
    
    @field_validator('damage')
    @classmethod
    def validate_damage(cls, v):
        if v <= 0:
            raise ValueError('damage must be greater than 0')
        return v
        
    @field_validator('current_hp')
    @classmethod
    def validate_current_hp(cls, v, info):
        """Ensure current HP doesn't exceed max HP."""
        max_hp = info.data.get('max_hp')
        if max_hp and v > max_hp:
            raise ValueError('current_hp cannot exceed max_hp')
        return v

    def take_damage(self, incoming_damage: int) -> int:
        """
        Apply damage to the enemy, accounting for armour.
        Returns the actual damage taken.
        """

        actual_damage = incoming_damage - self.armour

        self.current_hp = self.current_hp - actual_damage

        if(self.current_hp < 0):
            self.current_hp = 0

        return actual_damage
    
    def deal_damage(self) -> int:
        if self.current_hp <= 0:
            return 0
        
        variance = random.randint(-2, 2) # ±2 variance

        return self.damage + variance