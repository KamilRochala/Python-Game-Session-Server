import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
from dotenv import load_dotenv
import random
from typing import List, Dict, Any
from math import sin

from classes.weapon import Weapon, WeaponType
from classes.armour import Armour
from classes.accessory import Accessory, Stat
from classes.player import Player

from classes.enemy import Enemy

load_dotenv()

app = FastAPI()

class SelectionRequest(BaseModel):
    selected_index: int

def generate_reward(current_floor: int, is_healer: bool):
    reward_type = random.choice(["weapon", "armour", "accessory"])

    modifier_name = ["Big", "Small", "Sharp", "Dull", "Rusty", "Shiny", "Ancient", "Sturdy"]

    multiplier = (current_floor ^ 0.6) * (0.5 + 0.5(abs(sin(current_floor))))

    if reward_type == "weapon":
        weapon_name = ["Mace", "Sword", "Whip", "Greatsword", "Lance", "Spear", "Axe"]
        healer_name = ["Wand", "Staff", "Spellbook", "Spell"]
        
        random_mod = random.choice(modifier_name)
        
        if is_healer:
            name = random.choice(healer_name)
            item = Weapon(
                name=f"{random_mod} {name}",
                sprite_path=f"res://sprites/weapons/{name}.png",
                damage=random.randint(1, 5) * multiplier,
                healing_capacity=random.randint(5, 12) * multiplier,
                weapon_type=WeaponType.CLERIC
            )
        else:
            name = random.choice(weapon_name)
            item = Weapon(
                name=f"{random_mod} {name}",
                sprite_path=f"res://sprites/weapons/{name}.png",
                damage=random.randint(5, 15) * multiplier,
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
            defence_ammount=random.randint(1, 10) * multiplier,
            max_health_increase=random.randint(5, 20) * multiplier
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

def generate_enemies(current_floor: int, player_name: str):
    enemy_types = ["Slime", "Gremlin", "Skeleton", "Miner knight", "Rat man", "Wandering angel", "Mudman", "Frog sentiniel", "Lost paladin"]
    list_of_enemies = []

    number_of_enemies = random.randint(1, 5)
    multiplier = (current_floor^0.7)
    #random.choice

    for number in range(number_of_enemies):
        temp_enemy = Enemy(
            max_hp=random.randint(15, 25) * multiplier, 
            damage=random.randint(5,10) * multiplier, 
            armour=random.randint(2,4) * multiplier, 
            name="Ebstein" if player_name == "Ebstein" else random.choice(enemy_types)
        )
        list_of_enemies.append(temp_enemy)
        
    return list_of_enemies





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
            INSERT INTO items (name, sprite_path)
            VALUES (%s, %s) RETURNING id
        """, (choice["name"], choice["sprite_path"]))
        
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

        # Check if everyone else in the match is done
        cur.execute("""
            SELECT m.id, m.floor_number, m.player_1_id, m.player_2_id, m.player_3_id, m.player_4_id
            FROM matches m
            WHERE m.player_1_id = %s OR m.player_2_id = %s OR m.player_3_id = %s OR m.player_4_id = %s
        """, (player_id, player_id, player_id, player_id))
        match = cur.fetchone()

        if match:
            match_id = match["id"]
            player_ids = [pid for pid in (match["player_1_id"], match["player_2_id"], match["player_3_id"], match["player_4_id"]) if pid is not None]
            
            # Check if any player in this match still has pending choices
            cur.execute("""
                SELECT COUNT(*) as count 
                FROM pending_reward_choices 
                WHERE player_id = ANY(%s)
            """, (player_ids,))
            
            pending_count = cur.fetchone()["count"]
            
            if pending_count == 0:
                # Everyone has chosen, advance floor!
                current_floor = match.get("floor_number") or 1
                new_floor = current_floor + 1
                
                # Fetch a player name for the enemy generation
                cur.execute("SELECT player_name FROM players WHERE id = %s", (player_ids[0],))
                first_player = cur.fetchone()
                p_name = first_player["player_name"] if first_player else "Unknown"

                enemies = generate_enemies(new_floor, p_name)
                enemy_ids = []

                # Insert enemies
                for enemy in enemies:
                    cur.execute("""
                        INSERT INTO public.enemies (match_id, max_hp, current_hp, damage, armour, name)
                        VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
                    """, (match_id, enemy.max_hp, enemy.current_hp, enemy.damage, enemy.armour, enemy.name))
                    enemy_ids.append(cur.fetchone()["id"])

                # Update match
                cur.execute("""
                    UPDATE matches 
                    SET floor_number = %s, enemy_ids = %s 
                    WHERE id = %s
                """, (new_floor, enemy_ids, match_id))

        conn.commit()
        return {"status": "success", "item_type": choice["item_type"], "item_id": item_id}

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()

@app.post("/joinMatch/{player_id}")
def join_match(player_id: int):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # Check if player exists
        cur.execute("SELECT id FROM players WHERE id = %s", (player_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Player not found")

        # Check if player is already in an active match
        cur.execute("""
            SELECT id FROM matches 
            WHERE status IN ('waiting', 'in_progress') 
            AND %s IN (player_1_id, player_2_id, player_3_id, player_4_id)
        """, (player_id,))
        existing_match = cur.fetchone()
        
        if existing_match:
            return {"status": "already_joined", "match_id": existing_match["id"]}

        # Find an available waiting match with an open slot
        cur.execute("""
            SELECT * FROM matches 
            WHERE status = 'waiting' 
            AND (player_1_id IS NULL OR player_2_id IS NULL OR player_3_id IS NULL OR player_4_id IS NULL)
            ORDER BY id ASC LIMIT 1 FOR UPDATE
        """)
        match = cur.fetchone()

        if match:
            # Determine the first available slot
            slot_to_fill = None
            if match["player_1_id"] is None: slot_to_fill = "player_1_id"
            elif match["player_2_id"] is None: slot_to_fill = "player_2_id"
            elif match["player_3_id"] is None: slot_to_fill = "player_3_id"
            elif match["player_4_id"] is None: slot_to_fill = "player_4_id"

            # Update match with the player in the open slot
            cur.execute(f"UPDATE matches SET {slot_to_fill} = %s WHERE id = %s", (player_id, match["id"]))
            
            # If the match is now fully populated, we can mark it as in_progress
            if slot_to_fill == "player_4_id":
                cur.execute("UPDATE matches SET status = 'in_progress' WHERE id = %s", (match["id"],))

            conn.commit()
            return {"status": "success", "match_id": match["id"], "slot": slot_to_fill}
        else:
            # Create a brand new match since there are no waiting matches
            cur.execute("""
                INSERT INTO matches (status, player_1_id, floor_number) 
                VALUES ('waiting', %s, 1) RETURNING id
            """, (player_id,))
            new_match = cur.fetchone()
            
            conn.commit()
            return {"status": "success", "match_id": new_match["id"], "slot": "player_1_id"}

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()

@app.post("/startMatch/{match_id}")
def start_match(match_id: int):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # Check if match exists and is waiting
        cur.execute("SELECT id, status, player_1_id FROM matches WHERE id = %s", (match_id,))
        match = cur.fetchone()

        if not match:
            raise HTTPException(status_code=404, detail="Match not found")

        if match["status"] != "waiting":
            raise HTTPException(status_code=400, detail="Match is already in progress or finished")

        # Get player 1 name for enemy generation
        cur.execute("SELECT player_name FROM players WHERE id = %s", (match["player_1_id"],))
        player = cur.fetchone()
        player_name = player["player_name"] if player else "Unknown"

        # Generate floor 1 enemies
        enemies = generate_enemies(1, player_name)
        enemy_ids = []

        # Insert enemies
        for enemy in enemies:
            cur.execute("""
                INSERT INTO public.enemies (match_id, max_hp, current_hp, damage, armour, name)
                VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
            """, (match_id, enemy.max_hp, enemy.current_hp, enemy.damage, enemy.armour, enemy.name))
            enemy_ids.append(cur.fetchone()["id"])

        # Update match status to in_progress and add enemies
        cur.execute("""
            UPDATE matches 
            SET status = 'in_progress', enemy_ids = %s 
            WHERE id = %s
        """, (enemy_ids, match_id))

        conn.commit()
        return {"status": "success", "message": "Match started", "enemy_ids": enemy_ids}

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

@app.get("/getMatches")
def get_matches():
    # Connecting to the db
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        query = "SELECT * FROM matches WHERE status = 'waiting'"
        cur.execute(query)
        match = cur.fetchall()

        if not match:
            raise HTTPException(status_code=404, detail="Player not found")
            
        return match
    finally:
        cur.close()
        conn.close()