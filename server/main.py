import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
from dotenv import load_dotenv
import random
from typing import List, Dict, Any

from classes.weapon import Weapon, WeaponType
from classes.armour import Armour
from classes.accessory import Accessory, Stat
from classes.player import Player

load_dotenv()

app = FastAPI()

class SelectionRequest(BaseModel):
    selected_index: int

def generate_reward(current_floor: int, is_healer: bool):
    reward_type = random.choice(["weapon", "armour", "accessory"])

    modifier_name = ["Big", "Small", "Sharp", "Dull", "Rusty", "Shiny", "Ancient", "Sturdy"]

    if reward_type == "weapon":
        weapon_name = ["Mace", "Sword", "Whip", "Greatsword", "Lance", "Spear", "Axe"]
        healer_name = ["Wand", "Staff", "Spellbook", "Spell"]
        
        random_mod = random.choice(modifier_name)
        
        if is_healer:
            name = random.choice(healer_name)
            item = Weapon(
                name=f"{random_mod} {name}",
                sprite_path=f"res://sprites/weapons/{name}.png",
                damage=random.randint(1, 5) * (current_floor * 0.1),
                healing_capacity=random.randint(5, 12),
                weapon_type=WeaponType.CLERIC
            )
        else:
            name = random.choice(weapon_name)
            item = Weapon(
                name=f"{random_mod} {name}",
                sprite_path=f"res://sprites/weapons/{name}.png",
                damage=random.randint(5, 15) * (current_floor * 0.1),
                healing_capacity=0,
                weapon_type=WeaponType.KNIGHT
            )
        return item, "weapon"

    elif reward_type == "armour":
        armour_names = ["Chestplate", "Chainmail", "Robes", "Tunic"]
        name = random.choice(armour_names)
        item = Armour(
            name=f"{random.choice(modifier_name)} {name}",
            sprite_path=f"res://sprites/armours/{name}.png",
            defence_ammount=random.randint(1, 10) * (current_floor * 0.1),
            max_health_increase=random.randint(5, 20) * (current_floor * 0.1)
        )
        return item, "armour"

    else:
        acc_names = ["Ring", "Necklace", "Amulet", "Bracelet"]
        item = Accessory(
            name=f"{random.choice(modifier_name)} {random.choice(acc_names)}",
            sprite_path="res://sprites/accessories/.png",
            what_stat_is_multiplied=random.choice(list(Stat)),
            stat_multiplier=round(random.uniform(1.05, 1.5), 2)
        )
        return item, "accessory"

# Connection settings
DB_PARAMS = {
    "host": os.getenv('DB_HOST'),
    "database":  os.getenv('DB_NAME'),
    "user": os.getenv('DB_USER'),
    "password": os.getenv('DB_PASSWORD'),
    "port": os.getenv('DB_PORT')
}

def get_db_connection():
    return psycopg2.connect(**DB_PARAMS)

@app.get("/player/{player_id}")
def get_match(player_id: int):
    # Connecting to the db
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        query = "SELECT * FROM players WHERE id = %s"
        cur.execute(query, (player_id,))
        match = cur.fetchone()

        if not match:
            raise HTTPException(status_code=404, detail="Player not found")
            
        return match
    finally:
        cur.close()
        conn.close()

@app.post("/addPlayer")
def add_player(player: Player):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        params = {
            "name": player.player_name,
            "class": player.player_class,
            "max_health": player.base_max_health,
            "damage": player.base_damage,
            "healing_capacity": player.base_healing_capacity,
            "defence": player.base_defence
        }

        query_add_player = """
        INSERT INTO public.players(
        player_name, player_class, base_max_health, base_damage, base_healing_capacity, base_defence)
        VALUES (%(name)s, %(class)s, %(max_health)s ,%(damage)s , %(healing_capacity)s, %(defence)s) RETURNING *;
        """

        cur.execute(query_add_player, params)
        player_table = cur.fetchone()

        if not player_table:
            raise HTTPException(status_code=404, detail="Player not found")
        
        conn.commit()
            
        return player_table

    finally:
        cur.close()
        conn.close()

#@app.

@app.get("/rewardChoices/{player_id}")
def get_reward_choices(player_id: int):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # Check current floor by finding player's match
        query_check_player_match = """
        SELECT m.id, m.status 
        FROM matches m 
        WHERE m.player_1_id = %s OR m.player_2_id = %s OR m.player_3_id = %s OR m.player_4_id = %s
        """
        cur.execute(query_check_player_match, (player_id, player_id, player_id, player_id))
        match_row = cur.fetchone()
        
        # We assume floor is tied to match ID for now or defaults to 1
        current_floor = match_row["id"] if match_row else 1

        query_check_player_class = """
        SELECT player_class FROM players WHERE id = %s
        """
        cur.execute(query_check_player_class, (player_id,))
        player_row = cur.fetchone()
        
        if not player_row:
            raise HTTPException(status_code=404, detail="Player not found")
            
        is_healer = player_row["player_class"].lower() == "cleric"
        
        # Clear any existing choices for this player
        cur.execute("DELETE FROM pending_reward_choices WHERE player_id = %s", (player_id,))
        
        choices_response = []
        for i in range(1, 4):
            item, i_type = generate_reward(current_floor, is_healer)
            
            if i_type == "weapon":
                cur.execute("""
                INSERT INTO pending_reward_choices 
                (player_id, choice_index, item_type, name, sprite_path, damage, healing_capacity, weapon_class)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (player_id, i, i_type, item.name, item.sprite_path, item.damage, item.healing_capacity, item.weapon_type.value))
                
            elif i_type == "armour":
                cur.execute("""
                INSERT INTO pending_reward_choices 
                (player_id, choice_index, item_type, name, sprite_path, defence_amount, max_health_increase)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (player_id, i, i_type, item.name, item.sprite_path,item.defence_ammount, item.max_health_increase))
                
            elif i_type == "accessory":
                cur.execute("""
                INSERT INTO pending_reward_choices 
                (player_id, choice_index, item_type, name, sprite_path, stat_to_multiply, stat_multiplier)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (player_id, i, i_type, item.name, item.sprite_path, item.what_stat_is_multiplied.value, item.stat_multiplier))

            choices_response.append({
                "choice_index": i,
                "item_type": i_type,
                "item_data": item.model_dump()
            })
            
        conn.commit()
        return choices_response

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()

@app.post("/selectReward/{player_id}")
def select_reward(player_id: int, req: SelectionRequest):
    if req.selected_index not in [1, 2, 3]:
        raise HTTPException(status_code=400, detail="Invalid choice index. Must be 1, 2, or 3.")

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # Fetch the selected choice
        cur.execute("SELECT * FROM pending_reward_choices WHERE player_id = %s AND choice_index = %s", (player_id, req.selected_index))
        choice = cur.fetchone()

        if not choice:
            raise HTTPException(status_code=404, detail="No pending reward found for this index.")

        # Insert base item
        cur.execute("""
            INSERT INTO items (name, sprite_path, floor_multiplier)
            VALUES (%s, %s, %s) RETURNING id
        """, (choice["name"], choice["sprite_path"], choice["floor_multiplier"]))
        
        item_id = cur.fetchone()["id"]

        # Insert specific subtype and update player
        if choice["item_type"] == "weapon":
            cur.execute("""
                INSERT INTO weapons (item_id, damage, healing_capacity, weapon_type)
                VALUES (%s, %s, %s, %s)
            """, (item_id, choice["damage"], choice["healing_capacity"], choice["weapon_class"]))
            cur.execute("UPDATE players SET weapon_id = %s WHERE id = %s", (item_id, player_id))

        elif choice["item_type"] == "armour":
            cur.execute("""
                INSERT INTO armours (item_id, defence_amount, max_health_increase)
                VALUES (%s, %s, %s)
            """, (item_id, choice["defence_amount"], choice["max_health_increase"]))
            cur.execute("UPDATE players SET armour_id = %s WHERE id = %s", (item_id, player_id))

        elif choice["item_type"] == "accessory":
            cur.execute("""
                INSERT INTO accessories (item_id, stat_to_multiply, stat_multiplier)
                VALUES (%s, %s, %s)
            """, (item_id, choice["stat_to_multiply"], choice["stat_multiplier"]))
            # Assign to acc_slot_1 by default (could be extended later to manage inventory)
            cur.execute("UPDATE players SET acc_slot_1 = %s WHERE id = %s", (item_id, player_id))

        # Clear pending choices after successful selection
        cur.execute("DELETE FROM pending_reward_choices WHERE player_id = %s", (player_id,))

        conn.commit()
        return {"status": "success", "item_type": choice["item_type"], "item_id": item_id}

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()

@app.post("/createMatch/{player_id}")
def create_match(player_id: int):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        # 1) verify player exists
        cur.execute("SELECT 1 FROM players WHERE id = %s", (player_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Player not found")

        # 2) ensure player is not already in a non-finished match
        cur.execute(
            """
            SELECT id FROM matches
            WHERE (player_1_id = %s OR player_2_id = %s OR player_3_id = %s OR player_4_id = %s)
              AND status != %s
            LIMIT 1
            """,
            (player_id, player_id, player_id, player_id, "finished"),
        )
        if cur.fetchone():
            raise HTTPException(status_code=409, detail="Player already in an active match")

        # 3) insert new match and return id
        cur.execute(
            "INSERT INTO matches (player_1_id, status, floor_number) VALUES (%s, %s, %s) RETURNING id",
            (player_id, "waiting", 0),
        )
        match_id = cur.fetchone()["id"]
        conn.commit()

        return {"match_id": match_id, "status": "waiting", "floor_number": 0}

    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()