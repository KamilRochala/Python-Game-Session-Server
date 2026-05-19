from pydantic import (
    BaseModel,
    field_validator,
    ValidationError,
    ConfigDict,
    model_validator
)

from .weapon import Weapon
from .armour import Armour
from .accessory import Accessory, Stat
from .item import Item

from enum import Enum

# Remember the class with enums is with capital letters
class PlayerClass(str, Enum):
    KNIGHT = "knight"
    CLERIC = "cleric"

class Player(BaseModel):
    model_config = ConfigDict(validate_assignment=True) # If the value is updated, then it reruns the validation

    # General info
    player_name: str
    player_class: PlayerClass # This is an enum!!!!! remember

    # Stats
    base_max_health: float # This is before stat modifiers
    max_health: float = 0
    current_health: float = 0
    base_damage: float # This is before stat modifiers
    damage: float = 0 # This is after stat modifiers
    base_healing_capacity: float # This is before stat modifiers
    healing_capacity: float = 0
    base_defence: float
    defence: float = 0

    # Items
    weapon_slot: Weapon | None = None # Allow none in pydantic validation
    armour_slot: Armour | None = None
    accessory_slot_1: Accessory | None = None
    accessory_slot_2: Accessory | None = None
    accessory_slot_3: Accessory | None = None

    # Validators

    # For general info

    @field_validator('player_name')
    @classmethod
    def check_alphanumeric(cls, v: str) -> str:
        if not v.isalnum():
            raise ValueError('Username must be alphanumeric (small or big latin letter and a number)')
        return v
    
    @field_validator('player_class')
    @classmethod
    def check_if_valid_class(cls, v: PlayerClass) -> PlayerClass:
        allowed = [PlayerClass.KNIGHT, PlayerClass.CLERIC]
        if v not in allowed:
            raise ValueError('The class of the player is not allowed')
        return v
    
    # For Stats

    @field_validator('base_max_health')
    @classmethod
    def check_if_valid_base_max_health(cls, v: float) -> float:
        if v <= 0:
            raise ValueError('Too little max hp of a player')
        return v
    
    @field_validator('base_damage')
    @classmethod
    def check_if_valid_base_damage(cls, v: float) -> float:
        if v <= 0:
            raise ValueError('Base damage must be greater than 0')
        return v
    
    @field_validator('base_healing_capacity')
    @classmethod
    def check_if_valid_base_healing_capacity(cls, v: float) -> float:
        if v < 0:
            raise ValueError('Base healing capacity cannot be negative')
        return v

    # However, if after it turns out player is not cleric, then healing cannot be positive
    @model_validator(mode='after')
    def validate_healing_allowed(self):
        if self.player_class != PlayerClass.CLERIC and self.base_healing_capacity > 0:
            raise ValueError('Only clerics may have a base_healing_capacity > 0')
        return self
        
    # For items
    @field_validator('weapon_slot')
    @classmethod
    def check_if_valid_weapon(cls, v: Weapon) -> Weapon:
        if not isinstance(v, Weapon):
            raise ValueError('New Weapon is not a weapon type')
        return v

    # Model validator

    @model_validator(mode='after')
    def validate_stats(self):
        
        object.__setattr__(self, 'max_health', self.base_max_health)
        object.__setattr__(self, 'damage', self.base_damage)
        object.__setattr__(self, 'defence', self.base_defence)
        object.__setattr__(self, 'healing_capacity', self.base_healing_capacity)
        object.__setattr__(self, 'current_health', self.base_max_health)
        # Calculate multipliers from accessories
        damage_multipliers = 1.0
        health_multipliers = 1.0
        healing_multipliers = 1.0
        
        # Loop through all accessory slots
        for accessory_slot in [self.accessory_slot_1, self.accessory_slot_2, self.accessory_slot_3]:
            if accessory_slot is None:
                continue
            
            multiplier = accessory_slot.stat_multiplier * accessory_slot.floor_multiplier
            
            if accessory_slot.what_stat_is_multiplied == Stat.DAMAGE:
                damage_multipliers *= multiplier
            elif accessory_slot.what_stat_is_multiplied == Stat.MAX_HEALTH:
                health_multipliers *= multiplier
            elif accessory_slot.what_stat_is_multiplied == Stat.HEALING_CAPACITY:
                healing_multipliers *= multiplier
            elif accessory_slot.what_stat_is_multiplied == Stat.DEFENCE:
                current_def = self.defence if self.defence is not None else self.base_defence
                object.__setattr__(self, 'defence', float(current_def + accessory_slot.stat_multiplier))

        # If no weapon is equiped
        extra_dmg = self.weapon_slot.damage if self.weapon_slot else 0
        # Apply multipliers to final stats (bypass pydantic assignment hooks)
        object.__setattr__(self, 'damage', float((self.base_damage + extra_dmg  ) * damage_multipliers))
        object.__setattr__(self, 'max_health', float(self.base_max_health * health_multipliers))
        object.__setattr__(self, 'healing_capacity', float(self.base_healing_capacity * healing_multipliers))

        return self
    