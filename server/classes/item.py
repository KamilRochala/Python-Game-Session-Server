from pydantic import (
    BaseModel
)

class Item(BaseModel):
    name: str # Item's name
    sprite_path: str # Path to the item in godot
