from fastapi import FastAPI

from classes.player import Player, PlayerClass

app = FastAPI(title="Tower climb API")

# endpoints

# This endpoint in the body takes in:
# player_name: str
# player_class: str | we will use for example KNIGHT to play as him
#
# max_health: float | this and all of the similar ones will be assigned to base_max_health for example
# damage: float
# healing_capacity: float
# defence: float
#
# weapon: Weapon | this should be a dictionary with it's own values like damage and path to sprite
# armour: Armour
# accessory_1: Accessory
# accessory_2: Accessory
# accessory_3: Accessory

@app.post("/createCharacter", response_model=Player, status_code=201)
def create_player(payload: Player) -> Player:
    new_player = Player(
        # General Info
        player_name=payload.player_name,
        player_class=payload.player_class,

        # Health Stats
        base_max_health=payload.base_max_health,
        current_health=payload.max_health,  # Start at full health

        # Combat Stats
        base_damage=payload.base_damage,
        
        base_healing_capacity=payload.base_healing_capacity,
        
        base_defence=payload.base_defence,

        # Equipment Slots
        weapon_slot=payload.weapon,
        armour_slot=payload.armour,
        accessory_slot_1=payload.accessory_1,
        accessory_slot_2=payload.accessory_2,
        accessory_slot_3=payload.accessory_3
    )

    return new_player