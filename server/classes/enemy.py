from pydantic import (
    BaseModel
)

class Enemy(BaseModel):
    max_hp: int
    current_hp: int
    room_number: int
    damage: int
    armor: int